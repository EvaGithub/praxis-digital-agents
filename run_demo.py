"""
run_demo.py — Deterministic end-to-end pipeline runner.

Runs the FULL pipeline (scout -> audit -> sanitize -> report -> verify
-> demo site -> email draft -> dashboard) WITHOUT any LLM calls.

Why this exists: it is your demo-day safety net. If API quotas, WiFi,
or model latency fail during the presentation, this still produces
every artifact live in ~15 seconds. The agentic version (`adk run` /
`adk web`) adds LLM reasoning on top of the exact same tools.

Usage:
    python run_demo.py                    # fallback lead list
    python run_demo.py --live             # live DuckDuckGo search
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.lead_tool import find_leads, FALLBACK_LEADS
from tools.audit_tool import run_website_audit
from tools.report_tool import generate_pdf_report, draft_outreach_email, CHECK_LABELS_DE
from tools.report_visual import generate_visual_report
from tools.website_tool import generate_demo_website
from guardrails.sanitizer import sanitize_web_content
from guardrails.claim_verifier import verify_report_claims
from tools.rag_tool import retrieve_compliance
from config import PURSUE_THRESHOLD, MAX_LEADS

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")

TRAJECTORY = []

def log_step(lead: str, tool: str):
    """Append-only trajectory log — the substrate for the ordering eval."""
    TRAJECTORY.append({"lead": lead, "tool": tool})

GRADE_COLORS = {"A": "#27AE60", "B": "#F39C12", "C": "#E67E22", "D": "#E74C3C", "F": "#C0392B"}


def build_narrative(lead: dict, audit: dict) -> str:
    """Deterministic German narrative (the LLM writes a richer one in agent mode)."""
    failed = audit["failed_checks"]
    parts = [
        f"Die Website von {lead['practice_name']} erreicht {audit['score']} von "
        f"{audit['max_score']} Punkten (Note {audit['grade']})."
    ]
    if failed:
        labels = ", ".join(CHECK_LABELS_DE[c] for c in failed[:5])
        parts.append(f"Folgende Kriterien fehlen oder sind unzureichend: {labels}.")
    if "https" in failed:
        parts.append("Ohne HTTPS-Verschlüsselung warnen moderne Browser Ihre Patienten aktiv vor dem Besuch der Seite.")
    if "online_booking" in failed:
        parts.append("Eine Online-Terminbuchung fehlt — Patienten erwarten heute eine Buchung rund um die Uhr.")
    if "mobile_responsive" in failed:
        parts.append("Die Seite ist nicht für Smartphones optimiert, obwohl die Mehrheit der Patienten mobil sucht.")
    return " ".join(parts)


def run_pipeline(live: bool = False):
    print("=" * 64)
    print("SWISS MEDICAL PRACTICE AUDIT — deterministic pipeline")
    print("=" * 64)

    # 1. Scout
    if live:
        found = find_leads("Hautarzt", "Ostschweiz", max_results=MAX_LEADS)
    else:
        found = {"mode": "fallback", "count": len(FALLBACK_LEADS), "leads": FALLBACK_LEADS}
    print(f"\n[SCOUT] {found['count']} leads ({found['mode']} mode)")

    results = []
    for lead in found["leads"]:
        name = lead["practice_name"]
        print(f"\n--- {name} ({lead['url']}) ---")

        # 2. Audit
        log_step(name, "run_website_audit")
        audit = run_website_audit(lead["url"])
        if audit["status"] != "ok":
            print(f"[AUDIT] fetch failed: {audit.get('error', '')[:80]}")
            results.append({"lead": lead, "audit": audit})
            continue
        print(f"[AUDIT] {audit['score']}/{audit['max_score']} — Grade {audit['grade']} "
              f"— {len(audit['failed_checks'])} failed checks")

        # 3. Guardrail: sanitizer demo on page title/content marker
        log_step(name, "sanitize_web_content")
        san = sanitize_web_content(audit.get("page_title", "") + " sample page content")
        print(f"[GUARDRAIL] sanitizer risk={san['risk']}, flags={len(san['flags'])}")

        pursue = len(audit["failed_checks"]) >= PURSUE_THRESHOLD
        artifacts = {}
        eval_result = None

        if pursue:
            # 4. Narrative + claim verification eval
            narrative = build_narrative(lead, audit)
            log_step(name, "verify_report_claims")
            eval_result = verify_report_claims(narrative, audit)
            print(f"[EVAL] claim verification passed={eval_result['passed']} "
                  f"coverage={eval_result['coverage_of_failed_checks']}")

            # 5. Visual report (primary) + PDF (attachment version)
            safe = name.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", "")
            demo_url = f"demo_{safe}.html"
            log_step(name, "retrieve_compliance")
            legal = retrieve_compliance(audit["failed_checks"])
            print(f"[RAG] retrieved {len(legal['documents'])} compliance docs "
                  f"({', '.join(d['id'] for d in legal['documents'])})")
            log_step(name, "generate_visual_report")
            vis = generate_visual_report(audit, name, lead["doctor_name"],
                                         lead["specialty"], narrative, demo_url,
                                         legal_notes=legal["documents"])
            artifacts["report"] = os.path.basename(vis["report_path"])
            print(f"[VISUAL REPORT] {artifacts['report']}")
            pdf = generate_pdf_report(audit, name, lead["doctor_name"],
                                      lead["specialty"], narrative, demo_url)
            artifacts["pdf"] = os.path.basename(pdf["pdf_path"])
            print(f"[PDF] {artifacts['pdf']}")

            # 6. Demo website
            site = generate_demo_website(name, lead["doctor_name"],
                                         lead["specialty"], lead["city"])
            artifacts["demo"] = os.path.basename(site["html_path"])
            print(f"[DEMO SITE] {artifacts['demo']}")

            # 7. Email draft (human approval gate)
            top = ", ".join(CHECK_LABELS_DE[c] for c in audit["failed_checks"][:3])
            log_step(name, "draft_outreach_email")
            draft = draft_outreach_email(name, lead["doctor_name"], audit["grade"],
                                         audit["score"], top, demo_url)
            artifacts["draft"] = os.path.basename(draft["draft_path"])
            print(f"[OUTBOX] {artifacts['draft']} — {draft['status']}")
        else:
            print("[SKIP] site is healthy enough — not worth pursuing")

        results.append({
            "lead": lead, "audit": audit, "pursue": pursue,
            "artifacts": artifacts, "eval": eval_result,
            "sanitizer": {"risk": san["risk"], "flags": san["flags"]},
        })

    # 8. Dashboard
    dash = build_dashboard(results)
    print(f"\n[DASHBOARD] {dash}")
    with open(os.path.join(OUT, "run_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    with open(os.path.join(OUT, "trajectory.json"), "w", encoding="utf-8") as f:
        json.dump(TRAJECTORY, f, ensure_ascii=False, indent=2)
    print("[TRAJECTORY] trajectory.json saved")
    print("[STATE] run_results.json saved")
    print("\nPipeline complete. Open outputs/dashboard.html for the demo view.")
    return results


def build_dashboard(results: list) -> str:
    """Clickable HTML dashboard — the 'workable website' for demo day."""
    cards = []
    for r in results:
        lead, audit = r["lead"], r["audit"]
        if audit.get("status") != "ok":
            cards.append(f"""
    <div class="card">
      <h3>{lead['practice_name']}</h3>
      <p class="muted">{lead['city']} — {lead['url']}</p>
      <p class="err">Website nicht erreichbar</p>
    </div>""")
            continue
        g = audit["grade"]
        checks_rows = "".join(
            f'<div class="chk"><span>{CHECK_LABELS_DE[c]}</span>'
            f'<span class="{"ok" if p else "fail"}">{"✓" if p else "✗"}</span></div>'
            for c, p in audit["checks"].items())
        links = ""
        if r.get("artifacts"):
            a = r["artifacts"]
            links = f"""<div class="links">
        <a href="{a.get('report','')}" target="_blank">📊 Visueller Report</a>
        <a href="{a.get('demo','')}" target="_blank">🌐 Demo-Website</a>
        <a href="{a.get('pdf','')}" target="_blank">📄 PDF</a>
        <a href="../outbox/{a.get('draft','')}" target="_blank">✉️ Entwurf</a>
      </div>"""
        ev = r.get("eval") or {}
        eval_badge = ""
        if ev:
            ok = ev.get("passed")
            eval_badge = f'<span class="pill {"pill-ok" if ok else "pill-bad"}">Eval: Claims {"verifiziert ✓" if ok else "FEHLER"}</span>'
        san = r.get("sanitizer", {})
        san_badge = f'<span class="pill pill-neutral">Injection-Scan: {san.get("risk","-")}</span>'
        cards.append(f"""
    <div class="card">
      <div class="head">
        <div>
          <h3>{lead['practice_name']}</h3>
          <p class="muted">{lead['specialty']} — {lead['city']}</p>
          <p class="muted small">{audit['url']}</p>
        </div>
        <div class="grade" style="background:{GRADE_COLORS[g]}">{g}</div>
      </div>
      <div class="score">Score: <b>{audit['score']} / {audit['max_score']}</b> ({audit['percentage']}%)</div>
      <div class="pills">{eval_badge}{san_badge}</div>
      <details><summary>12 Kriterien anzeigen</summary><div class="checks">{checks_rows}</div></details>
      {links}
    </div>""")

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Praxis-Audit Dashboard — Multi-Agent System</title>
<style>
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0F1720; color:#E7EDF3; margin:0; padding:32px 20px; }}
.wrap {{ max-width:1150px; margin:0 auto; }}
h1 {{ font-size:1.7em; margin-bottom:4px; }}
.sub {{ color:#8CA0B3; margin-bottom:28px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr)); gap:20px; }}
.card {{ background:#18232F; border-radius:14px; padding:22px; border:1px solid #24313F; }}
.head {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }}
h3 {{ margin:0 0 4px; font-size:1.1em; }}
.muted {{ color:#8CA0B3; font-size:.88em; margin:2px 0; }}
.small {{ font-size:.78em; }}
.grade {{ min-width:54px; height:54px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:1.7em; font-weight:800; color:#fff; }}
.score {{ margin:14px 0 8px; font-size:.95em; }}
.pills {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }}
.pill {{ font-size:.72em; padding:4px 10px; border-radius:12px; }}
.pill-ok {{ background:#123B2A; color:#5BD99F; }}
.pill-bad {{ background:#42191D; color:#F08A8A; }}
.pill-neutral {{ background:#1F2C3A; color:#9FB5C9; }}
details summary {{ cursor:pointer; color:#6FB4E8; font-size:.88em; margin-bottom:8px; }}
.checks {{ margin-top:8px; }}
.chk {{ display:flex; justify-content:space-between; padding:5px 2px; font-size:.85em; border-bottom:1px solid #22303E; }}
.ok {{ color:#5BD99F; font-weight:700; }} .fail {{ color:#F08A8A; font-weight:700; }}
.links {{ display:flex; gap:14px; margin-top:14px; flex-wrap:wrap; }}
.links a {{ color:#6FB4E8; text-decoration:none; font-size:.88em; background:#1F2C3A; padding:8px 14px; border-radius:8px; }}
.links a:hover {{ background:#27394B; }}
.err {{ color:#F08A8A; }}
.foot {{ margin-top:30px; color:#5C6E80; font-size:.8em; }}
</style>
</head>
<body><div class="wrap">
<h1>🩺 Praxis-Audit Dashboard</h1>
<p class="sub">Multi-Agent System: Scout → Auditor (+ Injection-Guardrail) → Reporter (+ Claim-Verification-Eval) → Human Approval</p>
<div class="grid">{''.join(cards)}
</div>
<p class="foot">E-Mail-Entwürfe werden NIE automatisch versendet (UWG Art. 3 lit. o — Einwilligung erforderlich). Human-in-the-loop by design.</p>
</div></body></html>"""

    path = os.path.join(OUT, "dashboard.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


if __name__ == "__main__":
    run_pipeline(live="--live" in sys.argv)
