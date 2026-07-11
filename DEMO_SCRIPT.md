# PraxisDigital — Demo Script & Q&A Cheat Sheet

**Multi-Agent Audit & Outreach System for Swiss Medical Practices**
ADK 2.0 · Gemini 2.5 Flash · Built by Eva Losada Barreiro

> One-line pitch: *"Evidence beats pitching. Instead of cold-calling doctors with bad websites, the system proves the problem, builds the fixed version, and drafts the outreach — then stops and lets a human decide."*

---

## 0. Pre-demo checklist (do this 10 minutes before)

Run these once so every artifact is fresh and every number matches:

```bash
cd swiss_medical_audit_agents
source .venv/bin/activate
python run_demo.py            # regenerates all artifacts (~15s, no API needed)
python evals/run_evals.py     # should print: EVAL SUMMARY: 12/12 passed
```

**Open these tabs in advance (in this order):**
1. The real site — `http://www.hautarzt-herisau.ch` (the problem, live)
2. GitHub Pages — `https://evagithub.github.io/praxis-digital-agents/` *(verify it's live)*
3. `outputs/dashboard.html` — the operator dashboard
4. `outputs/report_hautarzt-herisau.html` — the visual audit report
5. `outputs/demo_hautarzt-herisau.html` — the rebuilt demo website
6. `outbox/draft_hautarzt-herisau.md` — the email draft (kept LOCAL/private)
7. A terminal, ready to run `adk web` and `python evals/run_evals.py`

**The numbers you will say (verify against your fresh dashboard):**
- Hautarzt Herisau → **20/90, Grade F, 9 failed checks** → full evidence package
- Haut & Laserzentrum Dr. Zuder → **67/90, Grade C, 3 failed checks** → correctly SKIPPED (healthy)
- Dermatologie Wil → **24/90, Grade F, 9 failed checks** → full evidence package
- Evals: **12/12 passing** · 12 checks worth 86 points · 3 parallel workers

> ⚠️ Note: the README body has been updated to cite **20/90** for Hautarzt Herisau. Use these numbers during your presentation.

---

## 1. The demo flow (≈6 minutes)

Each beat has **SHOW** (what's on screen) and **SAY** (your words).

### Beat 1 — The problem (45s)
**SHOW:** The real `hautarzt-herisau.ch` in the browser. Point at the `http://` (not `https`), the dated layout, no booking button.

**SAY:**
> "This is a real dermatology practice in Ostschweiz. Excellent doctors — but look: the site is HTTP-only, so browsers warn patients away from it. No online booking, in a country where one booking platform alone has three million patients. This practice loses patients it deserves, every day. Switzerland has thousands like it. The problem isn't the medicine — it's the shopfront."

### Beat 2 — The idea (30s)
**SAY:**
> "Web agencies sell doctors a website. They don't *find* the ones who need it, don't *prove* the problem, and don't *show* the fix before asking for money. My thesis is the opposite: evidence beats pitching. So I built a multi-agent system that finds these practices, audits them objectively, and produces a three-part evidence package — a diagnostic report, a rebuilt demo site, and a drafted email — all before a human ever gets involved."

### Beat 3 — The architecture (60s)
**SHOW:** The architecture diagram (README top, or GitHub Pages).

**SAY:**
> "Five parts. An **orchestrator** — an LLM — reads your request and delegates. Underneath it, a **fixed pipeline** enforced by code, not by the model's judgment: **Scout** finds practices, an **audit team** of three workers scores them *in parallel*, and a **Reporter** builds the evidence package. Wrapped around that: a **guardrail** that strips prompt-injection from every scraped page, an **eval gate** that checks every claim against the audit before publishing, a **legal RAG** that grounds legal statements in real Swiss law, and a **human approval gate** — because the one action with legal consequences, sending email, has no button anywhere in this system."

**Key phrases to land:**
- *"Order is code, not vibes"* — the LLM can't skip the audit.
- *"Deterministic where I want guarantees, LLM only where language actually helps."*

### Beat 4 — Live run (90s)
**SHOW:** Terminal → `adk web` → type: **"Audit dermatologists in Ostschweiz."** Watch the delegation and the three workers fan out.

**SAY (while it runs):**
> "The orchestrator perceives the request, then hands off to the pipeline. Scout returns the leads. Now watch — three audit workers run *at the same time*, because auditing a website is mostly waiting on it to load; parallel is roughly three times faster than one at a time. Each runs twelve objective checks in plain Python — HTTPS, mobile, booking, and so on — so the score is the same every single run. The AI only writes the interpretation on top; it never decides the score."

**Insurance:** if WiFi/API misbehaves, immediately run `python run_demo.py` — same tools, no LLM, produces every artifact in ~15 seconds. Say: *"Same pipeline, deterministic mode — my demo can't fail on stage."*

### Beat 5 — The evidence package (2 min)
**SHOW:** Walk the artifacts in order.

**a) The dashboard** (`dashboard.html`)
> "Every lead, its score and grade, and two badges per card: the injection-scan result and the eval verdict. Notice this one — Dr. Zuder, 67 out of 90, grade C — the system *skipped* it. It doesn't chase healthy sites. Two failing sites get the full package, one healthy one is left alone. That restraint protects both cost and credibility."

**b) The visual report** (`report_hautarzt-herisau.html`)
> "Semrush-style, in German, print-ready. A score gauge, the grade, four category bars, and twelve issue cards — each with the concrete fix. This is what proves the problem to the doctor."

**c) The demo website** (`demo_hautarzt-herisau.html`)
> "And this is the *solution*, already built — a premium, mobile, multilingual site with a booking card. We don't describe the fix; we hand it over."

**d) The email draft** (`outbox/draft_hautarzt-herisau.md`) — open LOCALLY
> "And the outreach email — drafted, personalized, with the demo link. But look at the top: 'REQUIRES HUMAN APPROVAL — DO NOT AUTO-SEND.' The recipient line even says '[VERIFY the address].' It's a draft, in a folder. Nothing is send-ready by accident."

*(Note: the PDF report and email draft are kept local/private — GitHub Pages intentionally links only the dashboard, report, and demo site.)*

### Beat 6 — The differentiators (60s)
**SHOW:** Terminal → `python evals/run_evals.py` → point at `12/12 passed`.

**SAY:**
> "Twelve evals, all passing. Five are prompt-injection attacks — a malicious site trying to hijack the agent — all caught. Three catch hallucinated findings, so a factually wrong audit never reaches a doctor. Two check that the right law is retrieved for the right failure. And two check the *order* of operations — that verification always happens before publication. This isn't decoration; it's the system's contract with itself."

### Beat 7 — The close (20s)
**SAY:**
> "The system drafts the email — and stops. There's no send function anywhere in the code; I checked, it isn't there, by design. Swiss law requires consent before commercial email, so a person reviews every draft. The most agentic decision in this whole system was deciding what the agents must never be able to do."

---

## 2. How to run it (for the "show me" moment)

| Mode | Command | What it proves |
|---|---|---|
| Agentic (the capstone) | `adk web` then "Audit dermatologists in Ostschweiz" | Real LLM orchestration, delegation, parallel fan-out |
| Deterministic (safety net) | `python run_demo.py` | Same tools, no API key, always works in ~15s |
| Evals (the evidence) | `python evals/run_evals.py` | 12/12 — injection, hallucination, retrieval, order |
| Deploy (the roadmap) | `adk deploy agent_engine --region europe-west6` | Same code runs hosted on Vertex AI (Zürich region) |

**Both modes call the same Python tools.** The LLM only adds narrative on top — that's why the deterministic fallback is a true safety net, not a different system.

---

## 3. Q&A cheat sheet (anticipated questions + honest answers)

**Q: Why multi-agent instead of one big prompt?**
> Separation of concerns and enforceable order. Each agent gets only the tools it needs (Scout can't audit, Reporter can't search) — that's confused-deputy prevention. And the pipeline order is a `SequentialAgent`, so the model structurally cannot publish before it audits.

**Q: Why run the audit workers in parallel?**
> Auditing = fetching a website = I/O-bound, mostly waiting. Three concurrent audits cut wall-clock roughly 3×. Parallelism pays exactly where the work is I/O, not CPU.

**Q: Why deterministic checks instead of asking the model "is this site good?"**
> Reproducibility and defensibility. I'm sending a real doctor a score — it must be identical every run and legally defensible, not a model's mood. Python scores; the LLM only interprets.

**Q: You read arbitrary websites — what about prompt injection?**
> Two layers. First, the design itself: the score comes from Python, so a malicious page can't corrupt the audit — there's no LLM in the scoring path to hijack. Second, the sanitizer: every scraped string that *can* reach the model — page body **and** the page title — is pattern-stripped and wrapped as untrusted data. Honest limit: regex isn't exhaustive; the documented upgrade is an LLM-firewall classifier.

**Q: How do you stop the AI hallucinating a finding?**
> The eval gate. Before publishing, every claim in the narrative is checked against the audit's ground-truth JSON. If it says "no booking" when booking passed, that's caught, and the Reporter rewrites — up to two tries, then falls back to a plain factual list built straight from the audit. So you always get a report, and it's always correct; only the eloquence degrades. Honest limit: it's a synonym/polarity heuristic, not semantic — upgrade path is LLM-as-judge.

**Q: What's the RAG, exactly? Is it scraping legal databases?**
> No — it's a hand-curated set of eight Swiss compliance facts, each a real statute (nDSG, UWG) summarized and tagged to the audit checks it applies to. When a check fails, it retrieves exactly the laws relevant to that failure, and the report cites only those — never legal claims from the model's memory. Keyword/tag retrieval, deliberately embedding-free at eight docs; upgrade path is Vertex vector search.

**Q: Can it accidentally spam doctors?**
> Structurally impossible — there is no send tool in the codebase. Drafts land in a folder with an approval header. That's Zero Ambient Authority: the risky action isn't discouraged by a prompt, it's absent from the code.

**Q: Is it deployed / production-ready?**
> The deployment path is proven — I've shipped ADK agents to Vertex Agent Engine before, and this runs the same way with one command. It's demo-ready, not yet hardened for public traffic: my threat model lists the exact steps before hosting — a private-IP blocklist on the fetcher, per-session quotas, and trace sampling.

**Q: What happens with more than three leads?**
> One worker per lead, three workers, so `MAX_LEADS` is capped at 3 in agentic mode — matched on purpose so no lead is found-but-never-audited. Scaling the agentic path means adding workers *and* raising the cap together; the documented growth path is wiring Scout to the Google Places API for ~100 practices/week.

**Q: What's next after demo day?**
> A decision gate: if the evidence-package approach validates, wire Scout to Google Places and scale; if not, keep the auditor + report core and pivot the outreach layer.

---

## 4. Honest caveats to volunteer (credibility > polish)

Saying these *before* you're asked reads as maturity:
- The claim verifier and injection filter are **heuristics** with documented LLM-based upgrade paths — they catch the common, high-likelihood failures cheaply and reproducibly.
- The legal KB is a **curated reference set**, not comprehensive or auto-updating — production needs a qualified review and a freshness process.
- The eval **gate + retry** is a bounded self-repair loop, soft-enforced by instruction in agentic mode; the *send* gate is the truly structural one (no tool).
- It's **demo-ready, not production-hardened** — and the threat model says exactly what's missing.

---

## 5. The three sentences to memorize

1. **"Order is code, not vibes — the model can't skip the audit."**
2. **"Python scores the site; the AI only writes the story — so the score is the same every run."**
3. **"The most agentic decision was deciding what the agents must never be able to do."**
