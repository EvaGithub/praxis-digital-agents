"""
Visual audit report generator — Semrush-style diagnostic report.

Produces a self-contained HTML report with score gauge, category
breakdowns, severity-coded issue cards, and a conversion CTA.
This is what gets sent to the doctor (as link or print-to-PDF).
"""

import os
from datetime import datetime
from typing import Union

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "outputs")

# check -> (label_de, category, severity_if_failed, fix_de)
CHECK_META = {
    "https":              ("HTTPS-Verschlüsselung", "Sicherheit & Vertrauen", "critical",
                           "SSL-Zertifikat installieren — Browser warnen Patienten aktiv vor unverschlüsselten Seiten."),
    "contact_form":       ("Sicheres Kontaktformular", "Sicherheit & Vertrauen", "warning",
                           "DSG-konformes Formular mit verschlüsselter Übertragung einrichten."),
    "update_recency":     ("Aktualität der Inhalte", "Sicherheit & Vertrauen", "warning",
                           "Inhalte aktualisieren und sichtbares Aktualisierungsdatum pflegen."),
    "mobile_responsive":  ("Mobile Optimierung", "Mobile & Geschwindigkeit", "critical",
                           "Responsive Design umsetzen — über 70% der Patienten suchen per Smartphone."),
    "page_load":          ("Ladezeit unter 3s", "Mobile & Geschwindigkeit", "warning",
                           "Bilder komprimieren, Caching aktivieren, modernes Hosting."),
    "google_business":    ("Google Business Profil", "Sichtbarkeit", "critical",
                           "Profil erstellen und verifizieren — entscheidend für lokale Suche und Maps."),
    "meta_description":   ("Meta-Beschreibung (SEO)", "Sichtbarkeit", "warning",
                           "Individuelle Meta-Beschreibungen für jede Seite hinterlegen."),
    "social_links":       ("Social Media Präsenz", "Sichtbarkeit", "info",
                           "Instagram/Facebook verknüpfen für Patientennähe."),
    "online_booking":     ("Online-Terminbuchung", "Patientenerlebnis", "critical",
                           "OneDoc Pro integrieren — 24/7 Buchung, Swiss-hosted, nDSG-konform."),
    "multilingual":       ("Mehrsprachigkeit", "Patientenerlebnis", "warning",
                           "DE/EN/FR-Versionen anbieten — Ihr Team spricht die Sprachen bereits."),
    "testimonials":       ("Patientenbewertungen", "Patientenerlebnis", "info",
                           "Google-Bewertungen einbinden für sozialen Beweis."),
    "broken_links":       ("Defekte Links", "Sicherheit & Vertrauen", "critical",
                           "Verzeichnispfad-Fehler (wie 'httpdocs/') beheben, damit Patienten die Unterseiten aufrufen können."),
}

CATEGORIES = ["Sicherheit & Vertrauen", "Mobile & Geschwindigkeit", "Sichtbarkeit", "Patientenerlebnis"]

SEV = {
    "critical": ("Kritisch", "#C73E3E", "#FBEBEB"),
    "warning":  ("Warnung", "#B07818", "#FBF3E2"),
    "info":     ("Empfohlen", "#3E6FA8", "#EAF1F9"),
    "passed":   ("Bestanden", "#2E7D5B", "#E8F4EE"),
}

GRADE_COLORS = {"A": "#2E7D5B", "B": "#7FA23B", "C": "#B07818", "D": "#C1622B", "F": "#C73E3E"}


def generate_visual_report(audit: Union[dict, str], practice_name: str, doctor_name: str,
                           specialty: str, narrative: str = "", demo_url: str = "#",
                           legal_notes: Union[list, str] = None) -> dict:
    """Generate the Semrush-style visual HTML audit report."""
    import json
    import ast
    if isinstance(audit, str):
        try:
            audit = json.loads(audit)
        except Exception:
            try:
                audit = ast.literal_eval(audit)
            except Exception:
                pass

    if isinstance(audit, str):
        import re
        failed_checks = []
        m = re.search(r"failed_checks[=:]\s*\[([^\]]*)\]", audit)
        if m:
            failed_checks = [c.strip().strip("'\"") for c in m.group(1).split(",") if c.strip()]
        score = 86
        m_score = re.search(r"score[=:]\s*(\d+)", audit)
        if m_score:
            score = int(m_score.group(1))
        grade = "F"
        m_grade = re.search(r"grade[=:]\s*([A-F])", audit)
        if m_grade:
            grade = m_grade.group(1)
        from tools.audit_tool import CHECK_POINTS
        max_score = sum(CHECK_POINTS.values())
        percentage = int(score / max_score * 100)
        checks = {c: (c not in failed_checks) for c in CHECK_POINTS}
        audit = {
            "score": score,
            "max_score": max_score,
            "percentage": percentage,
            "grade": grade,
            "failed_checks": failed_checks,
            "checks": checks,
            "status": "ok"
        }

    if isinstance(legal_notes, str):
        try:
            legal_notes = json.loads(legal_notes)
        except Exception:
            try:
                legal_notes = ast.literal_eval(legal_notes)
            except Exception:
                pass

    os.makedirs(OUT, exist_ok=True)
    safe = practice_name.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", "")
    path = os.path.join(OUT, f"report_{safe}.html")

    pct = audit["percentage"]
    grade = audit["grade"]
    gcolor = GRADE_COLORS[grade]
    checks = audit["checks"]

    # gauge geometry (donut, r=84, C=527.8)
    circumference = 2 * 3.14159 * 84
    dash = circumference * pct / 100

    # category scores
    cat_rows = ""
    for cat in CATEGORIES:
        cat_checks = [c for c, m in CHECK_META.items() if m[1] == cat]
        passed = sum(1 for c in cat_checks if checks[c])
        cpct = int(passed / len(cat_checks) * 100)
        bar_color = "#2E7D5B" if cpct >= 75 else "#B07818" if cpct >= 40 else "#C73E3E"
        cat_rows += f"""
      <div class="cat">
        <div class="cat-head"><span>{cat}</span><span class="cat-num">{passed}/{len(cat_checks)}</span></div>
        <div class="bar"><div class="bar-fill" style="width:{cpct}%;background:{bar_color}"></div></div>
      </div>"""

    # issue cards grouped by severity: critical first, then warning, info, passed
    def sev_of(check):
        return "passed" if checks[check] else CHECK_META[check][2]

    order = {"critical": 0, "warning": 1, "info": 2, "passed": 3}
    sorted_checks = sorted(CHECK_META.keys(), key=lambda c: order[sev_of(c)])

    cards = ""
    for c in sorted_checks:
        label, cat, _, fix = CHECK_META[c]
        s = sev_of(c)
        sname, scolor, sbg = SEV[s]
        body = (f'<p class="fix"><b>Massnahme:</b> {fix}</p>' if s != "passed"
                else '<p class="fix ok">Dieses Kriterium erfüllt Ihre Website bereits.</p>')
        cards += f"""
      <div class="card">
        <div class="card-top">
          <span class="chip" style="color:{scolor};background:{sbg}">{sname}</span>
          <span class="cat-tag">{cat}</span>
        </div>
        <h3>{label}</h3>
        {body}
      </div>"""

    n_crit = sum(1 for c in CHECK_META if sev_of(c) == "critical")
    n_warn = sum(1 for c in CHECK_META if sev_of(c) == "warning")
    n_pass = sum(1 for c in CHECK_META if sev_of(c) == "passed")

    narrative_html = f'<p class="narrative">{narrative}</p>' if narrative else ""

    legal_html = ""
    if legal_notes:
        items = "".join(
            f'''<div class="legal-item"><b>{d["topic"]}</b><p>{d["text_de"]}</p>
            <span class="src">{d["source"]}</span></div>''' for d in legal_notes)
        legal_html = f'''
<h2>Rechtliche Einordnung (nDSG / UWG)</h2>
<div class="legal">{items}</div>'''

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Digital-Audit — {practice_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{ --ink:#141B23; --paper:#F7F8F6; --line:#E2E5E0; --mut:#5B6570; --teal:#0E6E64; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter',sans-serif; background:var(--paper); color:var(--ink); line-height:1.6; }}
.wrap {{ max-width:960px; margin:0 auto; padding:0 24px 60px; }}
header {{ border-bottom:1px solid var(--line); padding:28px 0; margin-bottom:40px;
  display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:8px; }}
.brand {{ font-family:'Space Grotesk'; font-weight:700; letter-spacing:-0.02em; font-size:1.05rem; }}
.brand span {{ color:var(--teal); }}
header .date {{ color:var(--mut); font-size:0.82rem; }}
h1 {{ font-family:'Space Grotesk'; font-size:2.1rem; font-weight:700; letter-spacing:-0.03em; line-height:1.15; }}
.sub {{ color:var(--mut); margin-top:6px; font-size:0.95rem; }}
.hero {{ display:grid; grid-template-columns:220px 1fr; gap:48px; align-items:center;
  background:#fff; border:1px solid var(--line); border-radius:16px; padding:36px; margin:32px 0; }}
.gauge {{ position:relative; width:200px; height:200px; }}
.gauge svg {{ transform:rotate(-90deg); }}
.gauge-val {{ position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; }}
.gauge-val .n {{ font-family:'Space Grotesk'; font-size:3rem; font-weight:700; line-height:1; }}
.gauge-val .l {{ font-size:0.75rem; color:var(--mut); text-transform:uppercase; letter-spacing:0.08em; margin-top:4px; }}
.grade-pill {{ display:inline-block; font-family:'Space Grotesk'; font-weight:700; font-size:1.4rem;
  color:#fff; background:{gcolor}; padding:4px 18px; border-radius:8px; margin-bottom:10px; }}
.stats {{ display:flex; gap:28px; margin-top:18px; flex-wrap:wrap; }}
.stat .n {{ font-family:'Space Grotesk'; font-size:1.5rem; font-weight:700; }}
.stat .l {{ font-size:0.78rem; color:var(--mut); }}
.stat.crit .n {{ color:#C73E3E; }} .stat.warn .n {{ color:#B07818; }} .stat.ok .n {{ color:#2E7D5B; }}
.narrative {{ background:#fff; border-left:3px solid var(--teal); border-radius:0 12px 12px 0;
  padding:20px 24px; margin:0 0 36px; font-size:0.95rem; }}
h2 {{ font-family:'Space Grotesk'; font-size:1.25rem; font-weight:700; letter-spacing:-0.02em;
  margin:44px 0 18px; }}
.cats {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:28px 32px; }}
.cat {{ margin-bottom:18px; }} .cat:last-child {{ margin-bottom:0; }}
.cat-head {{ display:flex; justify-content:space-between; font-size:0.9rem; font-weight:600; margin-bottom:7px; }}
.cat-num {{ color:var(--mut); font-weight:500; }}
.bar {{ height:8px; background:var(--line); border-radius:4px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:4px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; }}
.card {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:20px 22px; }}
.card-top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
.chip {{ font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.06em;
  padding:3px 10px; border-radius:20px; }}
.cat-tag {{ font-size:0.72rem; color:var(--mut); }}
.card h3 {{ font-size:1rem; font-weight:600; margin-bottom:6px; }}
.fix {{ font-size:0.84rem; color:var(--mut); }}
.fix.ok {{ color:#2E7D5B; }}
.legal {{ background:#fff; border:1px solid var(--line); border-radius:16px; padding:10px 28px; }}
.legal-item {{ padding:16px 0; border-bottom:1px solid var(--line); }}
.legal-item:last-child {{ border-bottom:none; }}
.legal-item b {{ font-size:0.92rem; }}
.legal-item p {{ font-size:0.85rem; color:var(--mut); margin:5px 0; }}
.legal-item .src {{ font-size:0.72rem; color:var(--teal); font-weight:600; }}
.cta {{ background:var(--ink); color:#fff; border-radius:16px; padding:36px; margin-top:48px;
  display:grid; grid-template-columns:1fr auto; gap:24px; align-items:center; }}
.cta h2 {{ color:#fff; margin:0 0 8px; }}
.cta p {{ color:#B9C2CC; font-size:0.9rem; max-width:520px; }}
.cta a {{ display:inline-block; background:var(--teal); color:#fff; text-decoration:none;
  font-weight:600; padding:14px 28px; border-radius:10px; white-space:nowrap; }}
footer {{ margin-top:40px; padding-top:20px; border-top:1px solid var(--line);
  color:var(--mut); font-size:0.75rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }}
@media (max-width:720px) {{ .hero {{ grid-template-columns:1fr; justify-items:center; text-align:center; }}
  .cta {{ grid-template-columns:1fr; }} }}
@media print {{ body {{ background:#fff; }} .cta a {{ border:1px solid #fff; }} }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="brand">Praxis<span>Digital</span> Audit</div>
  <div class="date">Erstellt am {datetime.now().strftime('%d.%m.%Y')} • Vertraulich</div>
</header>

<h1>{practice_name}</h1>
<p class="sub">{doctor_name} • {specialty} • <span style="font-family:monospace">{audit['url']}</span></p>

<div class="hero">
  <div class="gauge">
    <svg width="200" height="200" viewBox="0 0 200 200">
      <circle cx="100" cy="100" r="84" fill="none" stroke="#E2E5E0" stroke-width="16"/>
      <circle cx="100" cy="100" r="84" fill="none" stroke="{gcolor}" stroke-width="16"
        stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}"/>
    </svg>
    <div class="gauge-val"><div class="n">{pct:.0f}%</div><div class="l">Online-Score</div></div>
  </div>
  <div>
    <div class="grade-pill">Note {grade}</div>
    <h2 style="margin:0 0 4px">Digitale Gesundheit Ihrer Praxis-Website</h2>
    <p style="color:var(--mut);font-size:0.92rem">{audit['score']} von {audit['max_score']} Punkten über 12 geprüfte Kriterien in 4 Kategorien.</p>
    <div class="stats">
      <div class="stat crit"><div class="n">{n_crit}</div><div class="l">Kritische Probleme</div></div>
      <div class="stat warn"><div class="n">{n_warn}</div><div class="l">Warnungen</div></div>
      <div class="stat ok"><div class="n">{n_pass}</div><div class="l">Bestanden</div></div>
    </div>
  </div>
</div>

{narrative_html}

<h2>Kategorien im Überblick</h2>
<div class="cats">{cat_rows}
</div>

{legal_html}

<h2>Alle 12 Kriterien im Detail</h2>
<div class="grid">{cards}
</div>

<div class="cta">
  <div>
    <h2>Wir haben eine Demo für Ihre Praxis gebaut</h2>
    <p>Sehen Sie, wie {practice_name} mit moderner, nDSG-konformer Website und 24/7 Online-Buchung auftreten könnte — unverbindlich und bereits personalisiert.</p>
  </div>
  <a href="{demo_url}">Demo ansehen →</a>
</div>

<footer>
  <span>Automatisch erstellt durch Multi-Agent Audit System • Alle Angaben ohne Gewähr</span>
  <span>Ausschliesslich für {practice_name}</span>
</footer>
</div>
</body>
</html>"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"report_path": path}
