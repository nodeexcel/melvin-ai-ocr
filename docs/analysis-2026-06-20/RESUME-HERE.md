# ▶ RESUME HERE — next-session quick-start (as of 2026-06-25)

**New session: read this + `MEMORY.md` first.** Full detail in `docs/analysis-2026-06-20/` — especially `07-melvin-meeting-2026-06-23.md` (client feedback) and `08-detail-callout-engine-design.md` (the core feature). Sonnet is fine for the work below; reserve Opus for hard design/debug only.

## Project in one line
AI construction estimator for **Melvin (Mel's Builders)**. **Takeoff-only** web app: upload structural-plan PDF → material takeoff (concrete / rebar / hardware / lumber). Stack: FastAPI + Next.js 14 + Postgres + Docker. Pipeline: `classify` (gpt-4o-mini) → `extract` (gpt-4o + gemini-2.5-flash) → `ocr` (PaddleOCR) → `aggregate` → `report` (reportlab).

## Deploy topology
- **Server** `pythonai@…:~/melvin-ai-ocr`, public at **http://116.202.210.102:20260**, deploys `origin/master`. Melvin tests here.
- **Local** repo `/home/lap-68/Documents/gt-atul/atul-melvin-architecture-analysis-and-analysis` (remote: github `nodeexcel/melvin-ai-ocr`).
- **Deployed = `591cc7a`.** Local `master` is **ahead by 2**: `947c69a` (Detail/ICC noise filter — CODE, *needs redeploy*) + `de2ed24` (docs).
- **Deploy steps:** local `git push origin master` → on server `git pull && docker compose build --no-cache backend frontend && docker compose up -d`. Server's local `docker-compose.yml` port change (20262) is intentional — leave it. After report-generator changes, also `UPDATE analysis_results SET report_pdf_path=NULL` so cached PDFs regenerate.

## DONE this session (deployed unless noted) — 11 commits `badfe8a..de2ed24`
- **Takeoff-only report** — pricing/labor removed (cost code kept dormant for a future pricing app).
- **Foundation-only LF OCR** (903.8→76.8 ft) + unified OCR orchestration (`runner.run_ocr_passes`, shared by CLI + web app).
- **Native JSON mode** (gpt-4o + gemini) — kills parse_errors.
- **Title-block address resolution** (8004 Gonzaga → 3333 Cabrillo).
- **Hardware cleaned at data layer** — new `app/pipeline/hardware.py` (`normalise_model`/`is_real_model`/`clean_*`): dedup, drop noise + pure-zero-qty, merge `HDU11*`==`HDU11`. raw_json now matches the PDF.
- **Report crash hardening** — LLM shape-variance guards (was 500-ing on Melvin's new plans).
- **Noise filter** — Detail-callout refs + ICC/NER report numbers dropped (`947c69a`, *not yet deployed*).
- Tests: `cd app/backend && PYTHONPATH=. ../../venv/melvin311/bin/python -m pytest tests/ --ignore=tests/test_pipeline.py` → **26 pass**. (`test_pipeline.py` is stale from the vision-first rewrite — needs a rewrite, low priority.)

## Client (Melvin) — what matters
- **Engaged 2026-06-23** (was unresponsive); **funded Gemini key**; asked **"when can we have the app ready?"**.
- **Scope:** takeoff-only, per-trade apps, **no pricing/labor**. Output = clean **Qty | Size | Length | Description**. **Quantities are the whole point.**
- **#1 feature:** detail-callout extraction. "HFX" = **Hardy Frame shear panels** (real Simpson product; his complaint was schedule-variant transcription, largely fixed).
- Sent **~10 plans + ~8 supplier EST lists** in `~/Downloads/`. **ASK HIM:** (a) full plan sets that **include the detail sheets**; (b) **which EST pairs with which plan** (needed to score accuracy).

## ★ CORE NEXT WORK — detail-callout engine (the project's value)
Feasibility **PROVEN end-to-end** on two real plans (`08` doc). Multi-modal: **text-layer path** (CAD plans, e.g. 8603 Rugby — callouts in selectable text) + **vision/OCR path** (raster/hand-lettered, e.g. 3611 Locke — chain `1/S4`→ST22/PC/PBS/LUS, `2/S4`→A307 bolts/SDS/A35 verified).
- **EXACT next step (NO API needed):** build **stage-2 text-layer callout detector** — regex `detail#/sheet#` pairs from a CAD plan's text layer, count per pair; validate on **8603 Rugby** text layer. Then the raster/vision path. See `08` §3 + §7.
- Design rules: key on full `detail#+sheet#` pair (numbers restart per sheet); classify marker shape (circle=detail / diamond=length / plain=gridline); validate model strings vs a Simpson allowlist (don't trust hand-lettered OCR blind — Rule 5).

## CONSTRAINTS (read before doing anything)
- **Claude Code usage limit reached (2026-06-25)** — caused by **Opus-1M high context** in this long session, **NOT** the project's OpenAI/Gemini API budget. Mitigation: **use Sonnet + fresh sessions**. The project's LLM keys are funded (Gemini) — **vision/OCR/pipeline runs are fine and NOT blocked.** (The text-layer detector + report polish happen to need no LLM calls anyway.)
- **Installs: venv ONLY** (`venv/melvin311/bin/pip ...`), never global, never sudo. OCR works in `venv/melvin311` (Py 3.11) + Docker; **crashes** on `app/backend/venv` (Py 3.13) and on heavy full-sheet **PP-Structure** (OOMs the 14 GB box — crop/downscale + cap threads if used).
- **Workflow:** spec → implement → commit. Stage only your own files — working tree has pre-existing WIP (`app/docker-compose.yml`, `app/frontend/package.json`) — never `git add -A`.
- **🔴 Exposed GitHub PAT** in the `origin` URL — **rotate it**. Live app has open security holes (CORS `*`+creds, JWT-in-URL, no upload cap) — ~1-day hardening before the URL spreads (see `02` F-1).
- **No reproducible baseline** — committed JSONs are stale; validate against fresh runs, not on-disk artifacts.

## Immediate options (pick one)
1. **Build the text-layer callout detector** (no API) — concrete core-feature progress now.
2. **Track A polish** (beams M-3, estimated-flags, connection-noise) → batch with `947c69a` → one redeploy.
3. **Run more of Melvin's plans / build the engine's vision path / score vs EST lists** — project LLM keys are funded (not blocked); just mind Claude Code session length (use Sonnet + fresh sessions).
4. **Reply to Melvin** — honest staged timeline + the two data asks above.
