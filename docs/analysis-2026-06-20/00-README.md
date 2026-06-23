# Engineering Analysis Workspace — AI Construction Estimator

**Session date:** 2026-06-20
**Analyst role:** Senior engineer / systems analyst / solution architect
**Mode:** Analysis & discovery only — **no implementation, no code changes** were made to the project. The only files written are the documents in this folder.
**Client:** Melvin Guzman — Mel's Builders Pro Systems
**Developer:** Atul (rahul@daden.dev)

---

## Purpose

This folder is an **independent analysis workspace** for a structured requirement-accuracy review of the project. It is deliberately separate from the project's own documentation (`docs/pipeline-findings.md`, `TODO.md`, etc.), which are the developer's working records. Nothing here changes project behavior.

## Documents

| File | Contents |
|---|---|
| `01-requirement-analysis.md` | Per-PDF review, the 10 requirements, business + technical observations, requirement→capability mapping |
| `02-findings-and-risks.md` | Verified findings, gaps, risks, architectural & operational concerns, ranked by severity |
| `03-decision-log.md` | Decisions taken during this analysis (with reasoning), reconstructed project decisions, recommendations & alternatives |
| `04-open-questions.md` | Clarifications needed, missing files/assets/specs/credentials, external & environment dependencies, blockers |
| `05-extraction-method-improvements.md` | Code-level improvement levers (file:line) + web-researched method choices (JSON mode, tiling, table-structure OCR, model upgrade, counting) + experiment log |
| `06-baseline-lhert-vs-ganahl.md` | First captured reproducible LHERT pipeline run vs the Ganahl EST618017 target; 6 root-caused current-code defects |
| `07-melvin-meeting-2026-06-23.md` | **FIRST client feedback.** Scope pivot (takeoff-only, per-trade apps), detail-callout extraction request, confirmed defects, re-prioritized roadmap |

## ⚡ Update 2026-06-23 — first client feedback received (see `07`)
Melvin reviewed a live report on a screen-share. **Scope is now resolved:** this app is **takeoff-only** (material list: concrete, rebar, hardware, steel, lumber) — **pricing and labor are dropped** from this app and become separate per-trade apps. He confirmed the **hallucination** problem (F-2) and that **quantities** are the whole point (F-9), and asked for a **detail-callout extraction** engine (detect callouts → resolve to detail sheets → extract + count hardware). He'll fund his own API keys (unblocks F-5). This update reframes the roadmap below — read `07` first.

## Method

1. Read the full requirement & design corpus: design spec, findings-and-feasibility, pipeline-findings, PLAN, CLIENT-REPORT, melvin-testing-guide, research-extraction-approaches, TODO, and the project memory.
2. **Ground-truthed all six sample PDFs** (provided by the client, in `~/Downloads/`) by reviewing each one's cover/title block, structural sheets, and a foundation/framing plan page — then cross-checking each against its committed extraction JSON in `app/backend/scripts/output/`.
3. **Verified the most consequential contradictions directly** against the JSON files (grep/parse) before asserting them as fact.

## Materials reviewed vs deferred

**Reviewed in full:** design spec (2026-05-20), findings-and-feasibility, pipeline-findings, PLAN (Phase 2), CLIENT-REPORT, melvin-testing-guide, research-extraction-approaches; memory: melvin_requirements, procurement_format, scope_gap, pipeline_state, web_app_state, user_preferences, feedback_no_patches, client_responsiveness; all 6 sample PDFs (representative pages); all 6 committed output JSONs. Backend pipeline + web app + frontend code were analysed in the immediately preceding session (security + architecture findings carried forward and re-verified where consequential).

**Deferred (covered transitively, low marginal value):** `research-explanation.md`, the two `docs/superpowers/plans/*` (implementation plans already reflected in shipped code), and memory files `project_overview`, `lf_extraction_findings`, `pdf_test_results`, `feedback_memory_updates` (their content is restated in `pipeline_state` / `TODO.md`, which were read in full).

---

## ⚠️ Two caveats that shape every conclusion

1. **The committed JSON outputs are stale, inconsistent snapshots.** They were generated on different dates (2026-05-25 → 2026-06-18) by different code versions, several of them in the **known-broken local Python-3.13 OCR environment**. They do **not** reflect the fixes claimed "done/confirmed" in `TODO.md`/memory. The validated successes (LHERT 76.8 ft LF, Gap-1 OCR→text producing 15 nailing entries) exist only in **uncaptured server/Docker runs** — they cannot be reproduced from anything in the repository. **There is no reproducible extraction baseline on disk.** This is itself a top finding (see `02`, F-4).

2. **Current-code behavior was not re-verified by running the pipeline.** Doing so would (a) violate the analysis-only constraint, (b) spend the developer's own API budget, and (c) fail locally anyway (PaddleOCR crashes on Python 3.13; the working path is Docker-only). So where a defect appears in a JSON artifact, this analysis states whether it is *likely still present* vs *plausibly fixed since*, and flags it for verification on the next legitimate run.

---

## Executive summary (the seven things that matter most)

1. **The product is ~30% of what was asked, and the missing 70% is mostly blocked by a hard physical limit, not effort.** Six of Melvin's ten requirements depend on *quantities* (linear feet, piece counts, concrete CY, sheathing) that live in **drawing geometry, not the PDF text/spec layer**. Ground-truthing the gold-standard project (LHERT SONG, for which we have the real $125k Ganahl order) confirms it: every hardware *type* is in clean schedule tables, but every *quantity* (LUS210 = 410, A35 = 500) is a "TYP." callout distributed across the plan grid — uncountable from text. This is the central business reality. (`01` §Data-availability; `02` F-9)

2. **The app is deployed LIVE on a public server** (`http://116.202.210.102:20260`, per `melvin-testing-guide.md`) **with serious security holes** — `CORS allow_origins=['*']` + `allow_credentials=True`, JWT in URL query strings, no upload size limit (a 216 MB sample exists), no rate limiting, default invite code `melvin2026`. These move from "hypothetical" to "active exposure." (`02` F-1)

3. **A core project rule is being violated: unverified quantities are returned unflagged.** CLAUDE.md Rule 5 says estimated numbers must carry `estimated: true`. The SVR JSON emits joist/beam/hardware quantities with **zero** `estimated` flags; the Woodlane JSON emits **fabricated** wood hardware (e.g. "Hurricane ties HT-10 ×20", "Lag bolt LB-5 ×15") that don't exist on the sheets. (`02` F-2)

4. **The OCR quantity path is broken in the environment that produced the artifacts.** The newest JSON (Paseo, 2026-06-18) shows **13 PaddleOCR runtime errors** (`ConvertPirAttribute2RuntimeAttribute`) and an **entirely empty project block** plus zero concrete/nailing/lumber — despite that data being plainly legible in the scanned pages. It reportedly works in Docker; the split (works in Docker / crashes on Python 3.13 local) is fragile and undocumented for operators. (`02` F-3, F-7)

5. **Production is gated by the Gemini free tier (20 requests/day).** One LHERT SONG run uses ~11; Woodlane lost 9 pages to 429 rate-limits in the committed run. The app cannot serve real usage until this is on a paid tier. (`02` F-5)

6. **Specification has drifted from reality, undocumented.** The design spec names **Claude Sonnet 4.5 + pdf2image/poppler + python-jose**; the system actually runs **GPT-4o + Gemini 2.5-flash + pypdfium2 + PaddleOCR + PyJWT/pwdlib**. Processing time is **20–45 min** (guide) vs the spec's **5–10 min**. (`02` F-11)

7. **The client is unresponsive and the developer self-funds the API.** Every "needs Melvin" item is blocked indefinitely; waiting is not a strategy. The right posture is *stabilize, decide sensible defaults, document, and stop expanding speculatively* — not build the hardest unvalidated features. (`03` D-7; `04` Q-block)

> Net assessment: this is **genuinely impressive, carefully-iterated work** with excellent documentation discipline. It is not, however, in a *trustworthy, reproducible, secure* state for production — and the largest requirement gap is a physics problem, not a backlog item. The highest-value next moves are corrective (baseline, security, honesty-of-output, scope decision), not additive.
