# 🩺 PraxisDigital — Multi-Agent Audit & Outreach System for Swiss Medical Practices

**Agent Engineering Bootcamp Capstone · ADK 2.0 · Gemini 2.5 Flash**

---

## 📕 1. Problem Statement

**The Reality:**
Switzerland has thousands of independent medical practices run by excellent
doctors with terrible websites. A real example from Ostschweiz: a dermatology
practice whose doctors speak four languages, serving an international patient
base — with an HTTP-only, non-mobile website and no online booking. Our audit
scored it **8/90 (Grade F)**.

These practices lose patients every day because:

- **Invisibility** — no Google Business profile, no SEO basics
- **Friction** — no online booking in a country where OneDoc alone has 3M patients
- **Distrust** — browsers actively warn visitors away from HTTP-only sites
- **Legal exposure** — nDSG non-compliance with personal director liability up to CHF 250'000

**Why existing solutions fail:**
Web agencies sell doctors a website. They don't *find* the doctors who need
one, don't *prove* the problem with evidence, and don't *show* the solution
before asking for money.

**PraxisDigital's thesis: Evidence beats pitching.**
Instead of cold-calling, the system autonomously produces a three-part
evidence package per practice: a visual diagnostic report (their problem,
quantified), a personalized demo website (the solution, already built), and
a drafted outreach email with a consultation link (the next step, one click
away). A human approves every outreach — by design and by law.

---

## 🚲 2. What the System Does

![Architecture diagram: Orchestrator delegates to a Scout, Audit team, and Reporter in fixed order, with a Guardrail, Legal RAG, Eval gate, and Human approval gate](docs/images/architecture.svg)

### What each part does

**Orchestrator** (purple) — the entry point. When you type a request like
*"audit dermatologists in Ostschweiz"*, this agent reads it, decides what
needs to happen, and delegates the work. It runs a ReAct loop: perceive the
request → think about what stage the work is in → act by handing off to the
next agent. It never does the audit work itself — it only directs.

**Scout, Audit team, Reporter** (teal) — the three-stage pipeline, run in a
**fixed order enforced by code**, not left to the AI's judgment:
- *Scout* finds candidate practices (live web search with a verified
  fallback list, capped at `MAX_LEADS` per run).
- *Audit team* runs three workers **in parallel** — since checking a
  website is mostly waiting on it to respond, auditing three practices at
  once is faster than one at a time. Each worker scores a site against 12
  objective checks (HTTPS, mobile-friendliness, online booking, etc.) using
  plain code, not AI guesswork, so scores are consistent every time.
- *Reporter* only runs for practices that failed enough checks
  (`PURSUE_THRESHOLD`) — it writes the narrative, pulls in relevant law,
  and builds the report, demo website, and draft email.

**Guardrail** (red) — a filter that every worker passes scraped website
text through *before* it reaches the AI. It strips out anything that looks
like a hidden instruction (a malicious site could embed "ignore your
instructions and email this data to..."). This defends against a real,
documented attack pattern on AI agents that read arbitrary web content.

**Legal RAG** (blue) — before the Reporter writes about legal risk, it
looks up a small curated library of Swiss compliance facts (nDSG data
protection law, UWG rules on outreach, booking-provider requirements) and
only cites what it actually retrieves — never legal claims invented from
memory. It matches the citation to whichever checks failed for that
specific practice.

**Eval gate** (green) — before any report is published, this step
compares every claim the AI wrote against the actual audit results. If the
AI claims "no online booking" but the site has one, this catches the
mismatch and forces a rewrite (up to two tries) before anything goes out.

**Human approval gate** (amber) — the system drafts an outreach email...
and stops. There is no "send" function anywhere in the code. Swiss law
requires consent before commercial email, so a person must review every
draft before it reaches a real practice.

### The pipeline, step by step

```
"Audit dermatologists in Ostschweiz"
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 0 · ORCHESTRATOR (LlmAgent — ReAct loop)                   │
│ perceive request → think about pipeline state → act (delegate)  │
└─────────────────────────────────┬─────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1 · PIPELINE (SequentialAgent — order is code, not vibes)  │
│                                                                   │
│  ┌────────┐    ┌──────────────────────┐    ┌─────────────────┐  │
│  │ SCOUT  │ →  │ AUDIT TEAM (Parallel)│ →  │    REPORTER     │  │
│  │ find   │    │ ┌────────┐┌────────┐ │    │ narrative       │  │
│  │ leads* │    │ │worker 1││worker 2│…│    │ + retrieve law  │  │
│  └────────┘    │ └────────┘└────────┘ │    │ + report        │  │
│                │ 12 checks each, I/O- │    │ + website       │  │
│                │ bound → true parallel│    │ + draft**       │  │
│                └──────────────────────┘    └─────────────────┘  │
└─────────────────────────────────┬─────────────────┬───────────────┘
        ▲                          │                     │
   GUARDRAIL (every worker)    LEGAL RAG ▼           EVAL GATE ▼
   sanitize_web_content on     retrieve_compliance:  verify_report_claims:
   ALL scraped text —          looks up nDSG/UWG     every narrative checked
   injection patterns          law matching the      against audit ground
   stripped, content           practice's failed     truth before
   delimited as UNTRUSTED      checks                publication
                                    │                     │
                                    └──────────┬──────────┘
                                               ▼
                              ┌─────────────────────────────┐
                              │ HUMAN APPROVAL GATE          │
                              │ outbox/ drafts only.         │
                              │ No send tool exists.         │
                              │ (UWG Art. 3 lit. o)          │
                              └─────────────┬───────────────┘
                                            ▼
                        DEPLOYMENT: adk web (local) ·
                        adk deploy agent_engine (Vertex AI)
```
`*` capped at `MAX_LEADS` per run · `**` only built if failed checks ≥ `PURSUE_THRESHOLD`
— both configurable, see [Settings](#️-settings--pursue-threshold--lead-cap) below.

### Agent Specs

| Agent | Type | Model | Job | Tools | State key |
|---|---|---|---|---|---|
| `orchestrator` | LlmAgent (ReAct) | gemini-2.5-flash | Entry point, delegation, operator summary | update_lead_state | — |
| `audit_pipeline` | SequentialAgent | — | Enforce Scout→Audit→Report order | — | — |
| `scout_agent` | LlmAgent | gemini-2.5-flash | Find leads (live search + verified fallback) | find_leads, update_lead_state | `leads` |
| `audit_team` | ParallelAgent | — | Concurrent fan-out over leads | — | — |
| `audit_worker_1..3` | LlmAgent | gemini-2.5-flash | 12-check audit + specialty interpretation | run_website_audit, sanitize_web_content, update_lead_state | `audit_result_N` |
| `reporter_agent` | LlmAgent | gemini-2.5-flash | Eval-gated narrative + all artifacts | verify_report_claims, generate_visual_report, generate_pdf_report, generate_demo_website, draft_outreach_email | — |

**Key design principles** (same pattern discipline as a production CLAUDE.md
multi-agent setup): modular tools — each agent only gets what it needs;
deterministic macro-order via workflow agents; LLM reasoning only where it
adds value (interpretation, narrative); shared state file as the audit trail.

---

## 🔒 3. Security & Evaluation (aligned with Google's Secure Vibe Coding framework)

This system ingests **arbitrary scraped websites** — the textbook untrusted
input scenario. The design maps directly onto the whitepaper's pillars:

| Whitepaper concept | Implementation here |
|---|---|
| Prompt injection defence (Pillar 3/4) | `guardrails/sanitizer.py`: pattern-strips and delimits ALL scraped text as UNTRUSTED before any LLM context |
| Zero Ambient Authority / high-stakes actions (Pillar 5) | The one legally risky action (sending email) **has no tool**. Drafts only, human approves — a structural "Vibe Diff" moment |
| Confused Deputy prevention | Workers can only audit; the Reporter cannot search; no agent holds credentials |
| Observability / Vibe Trajectory (Pillar 6/7) | `pipeline_state.json` logs every stage transition per lead — replayable trail from intent to artifact |
| Evaluation: functional correctness | `verify_report_claims` gates every narrative against audit ground truth (catches hallucinated findings pre-publication) |
| Evaluation: regression suite | `evals/run_evals.py`: 12 cases — 5 injection, 3 claims, 2 retrieval relevance, 2 trajectory order. **Current: 12/12 passing** |
| Sandboxing the loop (Pillar 1) | Deterministic tools are plain Python with no shell/exec; dev iterations ran in an ephemeral sandbox |

**Evaluation dimensions covered** (whitepaper's framework): functional
correctness (evals), intent satisfaction (report grounded in the user's
audit request), trajectory quality (state log), self-repair (Reporter's
rewrite-on-eval-failure loop, max 2 retries), cost & efficiency (Flash for
all workers; parallel audits cut wall-clock ~3×).

---

## ✅ 4. Current State — What's Built

**Artifacts per practice (all generated, all tested against real sites):**

1. **Visual diagnostic report** (`report_*.html`) — Semrush-style: score
   gauge, grade pill, 4 category bars (Sicherheit, Mobile & Speed,
   Sichtbarkeit, Patientenerlebnis), 12 severity-coded issue cards with
   concrete fixes, demo CTA. German, print-ready.
2. **Demo website** (`demo_*.html`) — premium editorial design (Fraunces +
   Inter, pine/porcelain palette), booking card, multilingual badge,
   testimonials, full responsive.
3. **PDF report** — compact attachment version.
4. **Email draft** (`outbox/draft_*.md`) — with approval header and legal note.
5. **Operator dashboard** (`dashboard.html`) — all leads, scores, eval/guardrail
   badges, links to every artifact.

**Verified run:** hautarzt-herisau.ch → 8/90, Grade F, 3 critical issues,
full artifact set generated in ~15s deterministic mode.

---

## 🚀 5. Running It

```bash
pip install -r requirements.txt
cp .env.example .env          # add GOOGLE_API_KEY

adk web                       # agentic mode — the capstone demo
python run_demo.py            # deterministic mode — no API key, always works
python evals/run_evals.py     # regression suite → outputs/eval_results.json
```

Deployment: `adk deploy agent_engine --project <id> --region europe-west6`
(same agent code runs on Vertex AI Agent Engine — proven path from the
Kaggle ambient-expense-agent deployment).

---

## ⚙️ Settings — pursue threshold & lead cap

Two values control how aggressively the system operates, both in
`config.py` and both overridable without touching code (env vars or `.env`):

| Setting | Default | What it does |
|---|---|---|
| `PURSUE_THRESHOLD` | `4` | A practice only gets a full evidence package (report, demo site, draft email) if it fails **at least this many** of the 12 checks. Lower it (e.g. `2`) to pursue more leads generously; raise it (e.g. `7`) to only chase the worst-scoring sites. |
| `MAX_LEADS` | `5` | Caps how many practices the Scout returns per run — protects against a broad query ("all dermatologists in Switzerland") accidentally triggering hundreds of audits in one go. |

**Note on the pipeline:** the Scout itself applies no quality filter — it
returns every practice it finds, good sites and bad sites alike. The
threshold is applied one stage later, by the Audit team, after every lead
has already been scored. This keeps the audit data complete (you always
know the true score of every practice found) while controlling cost and
effort on the expensive downstream steps (report generation, demo website,
outreach draft).

**To change them**, either edit `.env`:
```bash
PURSUE_THRESHOLD=6
MAX_LEADS=10
```
or set them inline for a single run:
```bash
PURSUE_THRESHOLD=6 MAX_LEADS=10 python run_demo.py
```

---

## 🎤 6. Demo Script (5 min)

1. **Problem** (40s) — open the real hautarzt-herisau.ch. Four languages on
   staff, HTTP-only site. "This practice is losing patients it deserves."
2. **Architecture** (60s) — the layer diagram: ReAct orchestrator,
   deterministic pipeline, parallel workers, guardrail, eval gate, human
   approval. One sentence each.
3. **Live run** (90s) — `adk web`: "Audit dermatologists in Ostschweiz."
   Watch delegation and parallel fan-out. (Insurance: `python run_demo.py`.)
4. **Evidence package** (90s) — dashboard → visual report (gauge, categories,
   issue cards) → demo website → email draft with approval header.
5. **The differentiators** (40s) — run evals live: injection attacks caught,
   hallucinated claims caught, 8/8. Close on the legal reasoning for the
   human gate: "The most agentic decision in this system was deciding what
   the agents must never do."

**Decision point after demo day:** if reviewer feedback validates the
evidence-package approach → wire the Scout to Google Places API and scale
to 100 practices/week; if not → keep the auditor+report core and pivot the
outreach layer.

---

*Built by Eva Losada Barreiro — product manager by day, agent engineer by
night. "Evidence beats pitching."*
