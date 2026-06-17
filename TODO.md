# Project TODO

**Project:** AI Construction Estimator — Mel's Builders Pro Systems  
**Last Updated:** 2026-06-14

---

## In Progress

- [x] Test pipeline on all 6 input PDFs ✅ COMPLETE
- [x] Scope resolved — V1 = specs + hardware + connections (what pipeline delivers). Quantity takeoff (CY, LF, counts) is V2. ✅
- [x] Write implementation plan → `docs/superpowers/plans/2026-05-21-web-app.md` ✅

---

## Pipeline — SVR 80% CD Set ✅ COMPLETE

Full extraction pipeline validated on `2026-03-31_SVR_80% CD Set.pdf`.

**Results (27 pages, 0 parse errors, 0 Vision calls, ~$0.00):**
- Project: SAN VICENTE RESIDENCE, 12957 SAN VICENTE BLVD., LA, CA, 13,717.74 sqft
- Structural engineer: MICHAEL ZAHN STRUCTURAL ENGINEERING
- Sheet list: 14 structural sheets (S0.1–S2.44)
- Nailing schedule: 11 entries (8d/10d/16d/20d/40d specs + header table)
- Lumber specs: 7 entries (Douglas Fir #2/#1, sheathing PS1-09)
- Concrete specs: 17 entries (2500 PSI foundations/slab)
- Simpson hardware: 52 items (HDU2/4/14, CMSTC straps, SDS screws, A34/A35, LSTA, LUS)
- Framing details: 49 connection items

**Known gap:** No S1 sheets — 80% set, foundation/framing plans not finalized yet.  
Wall `linear_feet` = 0 (A2 RCP pages, no labeled dimension annotations).

---

## Pipeline — Whaleon Residence CD Set ✅ COMPLETE

Full extraction pipeline validated on `2026-03-03 Whaleon Residence - CD Issue Set.pdf`.

**Results (7 pages, 0 parse errors, 6 Vision + 1 text, ~$0.07):**
- Project: WHALEON RESIDENCE, 364 E. PENTAGON ST. ALTADENA, CA 91001
- Architect/Structural engineer: Aram Arakelyan
- **Foundation data (first real foundation extraction!):**
  - F1 footing: 24" wide × 12" deep
  - F2 footing: 36" wide × 18" deep
  - Rebar: #4 @ 12" OC
  - Anchor bolts: 5/8" @ 48" OC
  - Hold-downs: HD1 ×4, HD2 ×2
- Simpson hardware: 12 unique items (H1, A35, H10, LUS26, H2.5A, HUCQ410, ABU88, HDU5/8/11)
- Framing connections: 9 entries across 3 detail sheets

**Known gaps:**
- `linear_feet` for footings = 0 (foundation plan dimensions are graphical, not labeled text)
- `concrete_cubic_yards` = 0 (same reason — needs dimension annotations in drawing)
- 66/73 architectural pages still unknown (A-series title block not in text layer)
- S-2.1 framing plan returned only notes (floor plan, graphical content)

**Key learning:** Whaleon structural pages (Aram Ark) have ~640 chars text (title block only) vs SVR pages (Zahn) with 3000–6000 chars. Threshold at 2000 chars correctly routes Whaleon to Vision and SVR to text.

---

## Pipeline — Other PDFs (do one by one)

### 1. BARAGHOUSH DD Progress ✅ COMPLETE
- [x] Run classification — 17 pages, all A-series architectural
- [x] DD set confirmed — architectural-only, no structural sheets
- **Result:** 0 relevant pages — nothing to extract
- **Key fix:** Added Pattern 4 (BARAGHOUSH title block: sheet# before "REVISION CLOUD SCHEDULE") and `"A-"` skip prefix. Patterns 3+4 now run before Pattern 1 to prevent false positive `S1`/`S2` skylight label matches.

### 2. Paseo Miramar RTI Stamped Plans ✅ COMPLETE
- [x] Confirmed zero text on all 57 pages
- [x] Built `test_pipeline_raster.py` — two-phase raster pipeline (batch thumbnail classify + Vision extract)
- [x] Classification: 37/57 structural pages flagged (includes some admin docs — harmless)
- [x] Extraction complete — concrete specs, nailing, steel connections, sheet list extracted
- **File:** `571 Paseo Miramar RTI Stamped Plans.pdf` (57 pages, 216MB)
- **Project:** HUNT RESIDENCE — Fire Rebuild, 571 Paseo Miramar, Pacific Palisades CA 90272
- **Structural engineer:** KOBE (pages 29–51)
- **Results:** `output/571_Paseo_Miramar_RTI_Stamped_Plans_results.json`
- **Key learnings:**
  - Raster pipeline works — real specs extracted from scanned plans
  - Dense soils notes pages (>8000 output tokens) fail silently — accepted limitation
  - Project info hallucination mitigated by targeted prompt instruction
  - `--rerun-pages` flag added for targeted re-runs without re-classification

### 3. Woodlane Court — All Plans ✅ COMPLETE
- [x] Run classification — 5 relevant pages
- [x] Extraction complete — 0 errors, ~$0.06
- **File:** `4248 Woodlane Court - All Plans.pdf` (60 pages, 144MB)
- **Project:** WLV 1 DEVELOPMENT RESIDENCE, 4248 WOODLANE COURT, WESTLAKE VILLAGE, CA 91362
- **SE:** JT Engineering Associates, Inc.
- **Result:** Architectural permit set only — no structural S sheets. T1 sheet confirms steel moment frame construction. 4 SMF CJP weld connection types extracted.
- **Fixes applied:**
  - Schedules → text routing (Vision was missing SE field by reading content instead of title block)
  - framing_details aggregation now pulls `connections` in addition to `hardware`
  - simpson_hardware filter: only items with `model` key included (prevents SMF weld descriptions from polluting hardware list)

### 4. LHERT SONG CD Bid Set ✅ COMPLETE
- [x] Run classification — 10 relevant pages (first run: 1 page, wrong — false positives)
- [x] Extraction complete — 0 errors, 2.0 min, ~$0.28
- **File:** `2025_09-30 LHERT SONG CD Bid Set.pdf` (64 pages, 35MB)
- **Project:** Lhert-Song, 3333 Cabrillo Blvd, Los Angeles, CA 90066
- **SE:** Ashley & Vance Engineering Inc. (Sean Galbreath, SE #5653)
- **Result:** 70 framing connections (best yet), concrete/lumber specs, foundation footings + rebar
- **Fix applied:** Pattern 5 — anchors to `AV JOB:` title block marker. Pattern 1 was matching `CC66`, `CS14`, `HDU2` hardware callouts as false-positive sheet numbers (column-order reading puts them before the title block)

---

## Pipeline — Cross-Firm Fixes (after testing all PDFs)

- [ ] **Cover sheet index parser** — architectural pages (A-series) for Whaleon and others
  - Strategy: extract text from pages 1–3 → find `[sheet_no] [title]` pairs → build page map
- [ ] **Foundation `linear_feet`** — GPT-4o reads footing type/size but not plan dimensions
  - Possible fix: add targeted prompt asking model to read dimension strings from drawing
- [ ] **Raster PDF pipeline** — Paseo Miramar (zero extractable text)
  - Vision-only classification + extraction for all pages
- [ ] **Test complete S1 structural set** — validate foundation/framing quantity extraction

---

## Pipeline — Code State (test_pipeline.py)

Current logic as of Paseo Miramar classification run:
- `TEXT_HEAVY_MIN_CHARS = 2000` — pages with >2000 chars use text extraction (raised from 500)
- `VISION_ONLY_CATEGORIES = {"floor_framing", "roof_framing", "foundation"}`
- `wall_framing` uses text (A2 RCP pages)
- `framing_details`: text if >2000 chars (SVR/Zahn style), Vision if <2000 chars (Aram Ark style)
- Text extraction: `max_tokens=8000`
- Vision extraction: `max_tokens=8000`
- Pattern 3 (Aram Ark): `"...A.A. S-2.0 1/4"=1'-0" FOUNDATION PLAN"` at end of text
- Pattern 4 (BARAGHOUSH): `"A-4.1 REVISION CLOUD SCHEDULE"` at end of text
- Patterns 3+4 run before Pattern 1 to prevent false positives from drawing body labels
- `"A-"` added to SKIP_PREFIXES — BARAGHOUSH-style `A-X.Y` architectural sheets
- Sheet mappings: `S-1 → schedules`, `S-2 → None (by title)`, `S-3/S-4 → framing_details`
- **New script:** `test_pipeline_raster.py` — raster-only pipeline using batch thumbnail classification (4 pages/call, `detail:low`) + full-res Vision extraction

---

## App Build ✅ COMPLETE (2026-05-21) — PDF report fully verified + post-launch fixes (2026-05-22)

- [x] Set up project with Docker + docker-compose (`app/` dir, docker-compose.yml, Dockerfiles)
- [x] FastAPI backend skeleton (main.py, config.py, database.py, lifespan handler)
- [x] PostgreSQL schema + Alembic migrations (User, Project, JobEvent, AnalysisResult; migration 001)
- [x] JWT auth (PyJWT[crypto] + pwdlib/bcrypt; POST /api/auth/login; get_current_user dep)
- [x] PDF upload endpoint (POST /api/projects/upload; path traversal fix; list/get/delete)
- [x] Background processing with ProcessPoolExecutor (pipeline_worker in separate OS process)
- [x] SSE progress stream (GET /api/projects/{id}/stream; own session; explicit SELECT; token query param)
- [x] GPT-4o Vision extraction pipeline (classify/extract/aggregate/prompts ported to app/backend)
- [x] PDF report generation (reportlab black/yellow brand; GET /api/projects/{id}/report)
- [x] Next.js 14 frontend (black+yellow theme, TypeScript, Tailwind 3)
- [x] Login page, dashboard, upload page, progress page (SSE live feed), results page
- [x] Docker compose wiring (db:5432, backend:8037, frontend:3036)
- [x] End-to-end smoke test (LHERT SONG: 10 pages, 43 connections, 7.8K PDF report ✅)

**Implementation plan:** `docs/superpowers/plans/2026-05-21-web-app.md`
**App directory:** `app/` (backend + frontend + docker-compose.yml)
**To start:** `cd app && docker compose up -d` then run migrations with `docker compose exec backend python -m alembic upgrade head`
**Note:** No `/api/auth/register` — create users via `docker compose exec backend python -c "...create_user()..."`

---

## Design / Spec Docs

- [x] Architecture design spec → `docs/superpowers/specs/2026-05-20-ai-construction-estimator-design.md`
- [x] Pipeline findings → `docs/pipeline-findings.md`
- [x] Findings + feasibility report → `docs/findings-and-feasibility.md`
- [x] Implementation plan → `docs/superpowers/plans/2026-05-21-web-app.md` ✅

---

## Post-Launch Fixes ✅ (2026-05-22 / 2026-05-23)

- [x] `docker-compose.yml` healthcheck: `pg_isready -d postgres` — stops FATAL DB spam in logs
- [x] React hydration errors #418/#423 — removed inline `typeof window` guards in progress/results pages
- [x] `ProgressFeed.tsx` fallback port: `8000` → `8037`
- [x] `report_pdf_url` always exposed for done projects — removed `report_pdf_path` gate in `routers/projects.py`
- [x] `generator.py` string guard for `lumber_specs`, `concrete_specs`, `nailing_schedule` (SVR stores as plain strings)
- [x] `generator.py` hardware table: zero-qty filter + dedup by model name
- [x] `generator.py` framing connections: Paragraph wrapping for proper word-wrap, column widths fixed
- [x] `ResultsPanel.tsx` empty value display: `[]`/`{}` → "None", arrays show "N items ▸" expandable
- [x] `generator.py` hardware dedup: normalise "Simpson " / "Simpson Strong-Tie " prefix so "Simpson H1" and "H1" merge into one row
- [x] `generator.py` empty section suppression: Foundation and Simpson Hardware headers only render when data exists (were always rendering even when empty)

## SVR 80% CD Set — Web App Run (2026-05-22)

- Uploaded via web app, processed correctly (~3 min)
- 55 hardware items, 95 framing connections, 45 nailing, 25 lumber, 17 concrete specs, 14 sheets ✅
- Foundation empty (0 footings, 0 rebar) — expected: 80% CD set, S1 foundation plans not finalized by SE
- This is a PDF gap, NOT a pipeline gap. 100% CD set will extract foundation data automatically.
- PDF report generates and downloads correctly (7 pages)

## Blocked / Waiting

- None — all known gaps resolved ✅

## ⚠️ CRITICAL GAP — Melvin's Full Requirements Not Met

V1 covers ~3 of 10 of Melvin's original requirements. Full requirements documented in `memory/melvin_requirements.md`.

**What Melvin asked for that is NOT built:**
- [ ] Framing lumber quantities — linear feet, piece counts (requires geometry reading from framing plans)
- [ ] Sheathing quantities — sheet counts (requires area calculation from floor/roof plans)
- [ ] Concrete yardage — CY (requires footing LF × cross-section, currently 0 on all PDFs)
- [ ] Rebar quantities — LF and piece counts (grade/spacing extracted but not quantities)
- [ ] Waste factors — field in schema always empty
- [ ] Procurement-ready material list — requires complete takeoff first
- [ ] Labor estimate — not in PDFs, must be calculated from quantities + rate sheet
- [ ] Equipment costs — not in PDFs, must be calculated
- [ ] Suggested construction schedule — derived output, not built

**What IS built (V1):**
- [x] Simpson hardware list (model + qty)
- [x] Lumber species/grade/design values (specs only, not quantities)
- [x] Foundation specs (PSI, rebar grade/spacing — not quantities)
- [x] Nailing schedule
- [x] Framing connection details
- [x] Project info, sheet list, SE

---

## Completed Tasks

- [x] Register endpoint for self-service user creation ✅ (2026-05-22) — `POST /api/auth/register` with invite code (`REGISTER_SECRET` in `.env`, default `melvin2026`). Register page at `/register`. Login page has "Need an account?" link.
- [x] ~~**Fix project info extraction**~~ — ✅ confirmed NOT broken. Data correctly extracted at `raw_json["project"]`. Earlier diagnosis used wrong lookup path. See `docs/pipeline-findings.md` Section 10.

## Remaining V2 Work

- [x] **Raster PDF support ✅ (superseded by Vision-first 2026-05-25):** Was Phase 1.5. `raster.py` deleted — Vision-first classification in `classify.py` handles raster and digital PDFs identically. Paseo Miramar: 31 relevant pages, 61 hardware, 160 connections extracted.
- [x] **Step 1 — Restructure ✅ (2026-05-25):** `app/backend/scripts/test_pdf.py` imports from `app.pipeline.runner` directly. Old `scripts/test_pipeline/` deleted. One codebase, no drift.

- [x] **Step 2 — Vision-first classification ✅ (2026-05-25):** `classify.py` replaced with Vision thumbnail classification (gpt-4o-mini, 4 pages/batch, detail:low). Firm-agnostic, handles mixed PDFs and any page ordering. `raster.py` deleted. Two-signal text cross-check prevents schedule page misclassification.

- [x] **aggregate.py most-common fix ✅ (2026-05-25):** Project name/address/SE now use most-common value across all pages. Fixes LHERT-SONG returning wrong address from early-page outliers.

- [ ] **GPT-4o Vision refusal handling (known limitation — not yet fixed):**
  - ~5-8% of Vision extraction pages return a refusal
  - Confirmed across all PDFs: Whaleon (3), Woodlane (7), LHERT SONG (4-5), SVR (3-4), Paseo (5)
  - Current behaviour: page silently skipped, `parse_error: True` in `_pages`
  - Proper fix: one retry per refused page with simplified prompt targeted at the category
  - Do NOT add a generic fallback — tune prompts per category
  - Low priority: refused pages are dense graphical drawings that return mostly zeros anyway

## Session 2026-06-08 — Keys received, next phase planned

- [x] **Melvin's API keys received and deployed ✅ (2026-06-08)**
  - OpenAI key: switched from dev key to Melvin's key (costs now bill to him)
  - Gemini key: added to `.env` + `docker-compose.yml` (`GOOGLE_API_KEY`)
  - Both keys confirmed live in running container
  - NOTE: Melvin should rotate both keys — they were sent over plain chat

- [x] **Gemini integration for Vision extraction ✅ (2026-06-08)**
  - `google-generativeai==0.8.5` added to requirements.txt, Docker image rebuilt
  - `GOOGLE_API_KEY` added to `config.py`, `docker-compose.yml`, `.env`
  - `extract_vision_gemini()` added to `extract.py` using `gemini-2.5-flash`
  - `GEMINI_CATEGORIES = {foundation, floor_framing, roof_framing}` in `runner.py`
  - Foundation/framing plan pages now route to Gemini, all other pages unchanged
  - `test_pdf.py` updated: `override=True` on dotenv, passes `google_api_key`
  - Whaleon validated: hardware 32→36, connections 46→53, 5 Gemini pages
  - Gemini extracts: hold_downs with qty, footing types P1-P4, rebar piece counts, anchor bolts

- [x] **PDF report quality improvements ✅ (2026-06-08)**
  - Footer on every page: company name (left) · generated date (centre) · page number (right) · yellow rule
  - Summary block under project header: "X hardware · X connections · X pages analyzed"
  - Header font 22→16pt (was wrapping to 2 lines)
  - New sections: Floor Framing Joists, Floor Framing Beams, Wall Framing, Roof Framing Rafters, Ridge Beam, Anchor Bolts
  - Filtered generic hardware names (Nails, Bolts, Strong-Tie, Holdown, etc.) from hardware table
  - Filtered blank connection rows (no hardware + no lumber sizes) from connections table
  - `_std_table()` helper refactored to remove repeated TableStyle code

- [x] **Frontend ResultsPanel improvements ✅ (2026-06-08)**
  - `_pages` hidden from results view (was showing "35 items" of internal debug data)
  - Sheet list: `S0.1 — Structural Notes` instead of raw JSON
  - Hardware: `HDU4 ×10` instead of raw JSON
  - Connections: show description field directly

- [x] **Vision refusal retry ✅ (2026-06-08)**
  - `is_refusal()` + `RETRY_PROMPTS` in `prompts.py` — 15 refusal phrases detected
  - Both `extract_vision()` (GPT-4o) and `extract_vision_gemini()` retry once on refusal
  - Retry prompt is short + annotation-focused per category
  - Whaleon: 2-3 errors → 0 errors. Refusal pages now recover data.

## Session 2026-06-09 — Phase 2 LF extraction investigation

- [x] **Gemini dimension extraction attempt ✅ (investigated, partially works)**
  - Added `DIMENSION_PROMPTS` in `prompts.py` — short focused prompts asking for scale + LF
  - Added `extract_dimensions_gemini()` in `extract.py` — separate second Gemini call on Gemini pages
  - Added `estimated`/`drawing_scale` fields to foundation/floor_framing/wall_framing/roof_framing in aggregate.py
  - Added `" *"` suffix on estimated columns in PDF report + verification note
  - **Result: Gemini reads drawing scale correctly (1/4"=1'-0") but returns 0 for all LF fields**
  - **Root cause: dimension callouts on CAD PDFs are vector-rendered graphical text — not in PDF text layer, not readable by Gemini's spatial reasoning**
  - The dimension architecture (separate pass, estimated flag, PDF display) is complete and correct

- [x] **PyMuPDF vector extraction investigation ✅ (investigated, not viable for these PDFs)**
  - `pymupdf` installed in venv
  - Tested on Whaleon p68 (foundation plan): 30,712 stroke paths, 107,439 line segments, 1,240 long lines
  - ALL lines are black (0,0,0) — can't filter by color to isolate footing lines
  - Dimension text NOT in PDF text layer (only 102 words on page, all title block)
  - Too many undifferentiated lines to reliably identify footing perimeter without CAD layer info
  - **Not viable for these specific CAD-generated PDFs without DXF/layer access**

- [x] **PaddleOCR + full LF pipeline ✅ (2026-06-09)**
  - Docker backend is `python:3.11-slim` → PaddleOCR works in Docker ✅
  - `app/backend/app/pipeline/ocr.py` — PaddleOCR module (tiled rendering, dedup, feet-inches parsing, footing filter, graceful fallback)
  - `scripts/ocr/extract_lf.py` — standalone CLI for testing (Python 3.11 venv/melvin311)
  - `aggregate.py inject_lf_data()` — distributes LF to footing types, calculates CY from LF × avg footing cross-section
  - `runner.py pipeline_worker` — calls OCR after main extraction, injects LF data
  - `requirements.txt` + `Dockerfile` — PaddleOCR 3.3.0 + PaddlePaddle 3.2.0 + pymupdf + libgl1
  - Docker image rebuilt and verified: `PaddleOCR available: True` ✅
  - PDF report already shows: LF* in footing table, CY* estimate, `" *"` estimated flag, verification note
  - Full run validated: 128.6 LF from Paseo Miramar p35/37/38, CY = 14.3 ✅

## Session 2026-06-12 — Web app test, PDF fixes, honest gap assessment

- [x] **classify.py prompt fix ✅ (2026-06-12)**
  - Added KEY VISUAL RULE: plan view pages (overhead building footprint) → foundation/floor_framing/roof_framing even with detail callouts
  - Result: Paseo Miramar p35/37/38 now correctly classified. 4 OCR-eligible pages found vs 0 before.

- [x] **End-to-end web app test ✅ (2026-06-12)**
  - Uploaded Paseo Miramar via localhost:3036
  - Pipeline ran: 34 relevant pages, 154 framing connections, 23 hardware items, GBM1/GBM2 footings, anchor bolts, PSL beams
  - OCR triggered (3 pages) but returned {} due to Docker libpaddle.so conflict
  - PDF generated and downloaded — 9 pages, all sections rendering

- [x] **PDF report: full-width tables + remove sheet list ✅ (2026-06-12)**
  - All tables now sum to 7.0" (usable page width) — hardware, footing, rebar, anchor bolts, framing sections
  - Sheet list removed from PDF (was 9 pages of S1-S100 in Paseo set, not useful in print)
  - PDF cache cleared, generator deployed to container

- [x] **Docker OCR — libgomp1 was the root cause ✅ (2026-06-12)**
  - Real error was `libgomp.so.1: cannot open shared object file` — OpenMP not in python:3.11-slim
  - Added `libgomp1` to apt-get install in Dockerfile
  - Pinned `python:3.11.0-slim` + pip constraints to prevent paddlepaddle version conflict
  - PaddleOCR now loads in Docker: `OCR instance: PaddleOCR, Works: True`
  - Full test: Paseo Miramar LF = 128.6 ft, CY = 10.7 ✅ showing in PDF report

- [x] **Summary count bug ✅ (2026-06-12)**
  - Fixed: `hw_count` now checks `qty_mentioned` as fallback — shows "45 hardware items" correctly

- [x] **Beam table bloat ✅ (2026-06-12)**
  - Fixed: joists/beams/rafters pre-filtered to only rows with at least one non-zero numeric value

- [ ] **Hardware table: "OHAGIN ROOF VENT" and generic items**
  - "OHAGIN ROOF VENT" is not structural hardware — should be in non-Simpson blocklist
  - "SIMPSON CMSTC16" etc — normalizer strips "Simpson " but not "SIMPSON " (uppercase)
  - Fix: add uppercase prefix normalization + "OHAGIN", "ROOF VENT" to GENERIC blocklist

## Current honest gap assessment (2026-06-12)

**Fully done:**
- Simpson hardware list (models + quantities) ✅
- Lumber specifications (species, grade, design values) ✅
- Concrete PSI specs ✅
- Rebar grade/spacing ✅
- Foundation specs (footing types + dimensions, anchor bolts, hold-downs) ✅
- Nailing schedules ✅
- Framing connection details ✅
- Floor/wall/roof framing sections in PDF (sizes, spacing, spans) ✅
- Web app end-to-end (upload → process → PDF download) ✅
- PDF branding, footer, page numbers ✅

**Partially done (quantities = 0 or partial):**
- Footing LF — works via test script on scanned PDFs only; 0 on CAD PDFs and 0 in web app (Docker OCR)
- Concrete CY — calculated when LF > 0; 0 everywhere in web app
- Rebar piece counts — extracted correctly; LF still 0
- Joist/beam spans extracted; piece counts and LF = 0

**Not built:**
- Sheathing sheet counts
- Procurement-ready material list
- Waste factors
- Labor estimates (Phase 3 — needs RSMeans)
- Equipment costs (Phase 3)
- Construction schedule (Phase 3)

## Session 2026-06-13 — Melvin's procurement list received (CRITICAL)

- [x] **Received Ganahl Lumber estimate #618017 ✅ (2026-06-13)**
  - Job: LHERT-SONG (3333 Cabrillo Blvd) | Total: $125,665.15
  - This is the GOLD STANDARD for what Phase 2 output must produce
  - Saved to memory/procurement_format.md — read before every Phase 2 session

**Key findings from the real order:**

- **Format**: Qty | Size | Length | Grade | Board Footage | Price | Amount
- **Organized by construction phase**: Material → 1st Floor → 2nd Floor → Ceiling (NOT by data type like our current report)
- **Simpson hardware quantities**: LUS210=410pcs, HDU4=27pcs, HDU8=19pcs, A35=500pcs, LUS28=200pcs, CMST12=10pcs, DTT2Z=10pcs, HGA10KT=30pcs — our extraction captures the RIGHT models but undercounts quantities
- **Lumber counts we don't have**: 195 pcs 2x6x10, 80 pcs 2x6x12, 300 ITS2.06 I-joist hangers, etc.
- **TJI I-joists**: 300+ pieces of 11-7/8" TJI-210/230 — not extracted anywhere
- **Plywood**: 86 sheets 4x8 23/32 subfloor, 104 sheets 4x8 19/32 sheathing — not calculated
- **Fasteners**: foundation bolts, wedge anchors, all-thread rods, nails — not in scope

**What this tells us about Phase 2 priority:**
1. Lumber piece counts by size/length/floor — highest value
2. Plywood/sheathing sheet counts — second priority
3. Reorganize output BY FLOOR (not by type)
4. Hardware quantities are directionally right but need improvement

## Phase 2 Plan (from docs/PLAN.md)

- [x] **Priority 1 — Hardware schedule extraction ✅ (2026-06-13)**
  - OCR callout counting from plan pages: CMST12×4, ST6236×6, HDU11×1 etc.
  - Fast low-res pass (0.7x, ~5s/page) for hardware counting
  - Full tiled pass (1.5x) for LF extraction
  - Both wired into pipeline_worker + test_pdf.py (module import + subprocess fallback)

- [x] **Priority 2 — Phase-based output reorganization ✅ (2026-06-13)**
  - `hardware_by_phase` dict in aggregate.py + _phase_for_model() heuristics
  - Render-time redistribution in generator.py (_redistribute_phases, _hw_phase)
  - Works on cached results too — no re-run needed
  - PDF now shows: Foundation / Floor Framing / Wall Framing / Roof Framing / General
  - Generic items filtered (OHAGIN ROOF VENT, Nails, HSS, etc.)
  - Old redundant Simpson Hardware Schedule hidden when phase section present
  - Validated: estimate (23) — HDU foundation, LUS floor, CMST wall, H1/H2.5A roof ✅
  - Remaining: B1/W1/S1/AB123 uncertain codes — ask Melvin to verify

- [ ] **Priority 1 — Hardware schedule extraction** (HIGH VALUE, START HERE)
  - Read hold-down + strap + joist hanger SCHEDULE TABLES from plan pages via OCR
  - Evidence: Paseo p35 has GRADE BEAM SCHEDULE with HDU4×13, HDU8×14 — readable
  - This is why real order has HDU4=13 but we extract ~3 (we read callouts, not schedules)
  - Files: ocr.py (schedule table parser), aggregate.py (merge schedule + Gemini hardware)

- [x] **Priority 2 — Phase-based output reorganization ✅ (see above)**

- [ ] **Priority 3 — Quantity estimation module (NEXT)**
  - Use extracted specs (stud size/spacing, joist spacing) + total_sqft → estimated piece counts
  - Standard CA residential factors: studs per LF wall, joists per sqft floor, plywood sheets
  - New file: app/pipeline/quantities.py
  - Mark all as estimated: true, organized by phase to match Ganahl format
  - Reference: memory/procurement_format.md (Ganahl EST618017 gold standard)

## Current State — 2026-06-14 (post estimate 25 validation)

### What's working in production
- Hardware Schedule by Phase: Foundation/Floor/Wall/Roof/General all correct ✅
- Phase redistribution at render time (works for cached results) ✅
- Preliminary Quantities: 87 sheets subfloor vs real order 86 — essentially exact ✅
- OCR callout counting: CMST12×4, ST6236×6, HDU11×1 etc. from plan pages ✅
- LF + CY for scanned PDFs (Paseo Miramar: 128.6 ft) ✅
- PDF: footer, phase section, quantities section, 5 clean pages ✅

### Remaining — Short Term (code changes, no external dependency)

- [x] **#1 INDEPENDENT — Page 5 waste ✅ (2026-06-14)**
  - connections table TOPPADDING/BOTTOMPADDING 4→2pt; 5-page PDF → 4-page PDF

- [x] **#2 INDEPENDENT — Wall stud default fallback ✅ (2026-06-14)**
  - quantities.py: when Gemini doesn't return stud_size, default to 2x6@16" ext / 2x4@16" int
  - 472 exterior studs + 708 interior studs now generated for 2,509 sqft
  - Floor joist quantities still 0 (Gemini extracts joist sizes inconsistently)

- [x] **#3 INDEPENDENT — TJI prompt ✅ (2026-06-14)**
  - prompts.py floor_framing: added explicit TJI/I-joist instruction with model capture
  - Effect: next fresh run should return size="11-7/8 TJI-210" instead of generic "TJI"

- [x] **#4 INDEPENDENT — Foundation classification override ✅ (2026-06-14)**
  - classify.py: if text layer has FOUNDATION PLAN/FOOTING PLAN, override to foundation
  - Doesn't fire if already schedules or skip (schedule override takes precedence)

- [x] **#5 INDEPENDENT — B1/W1/S1 filter ✅ (2026-06-14)**
  - generator.py _is_real_model(): 2-char non-H codes filtered; H1/H2 still pass

- [ ] **#6 NEEDS MELVIN — Hardware quantities still low**
  - LUS210×12 extracted vs real order LUS210×380+
  - "TYP." connections repeated throughout plans not captured by callout counting
  - Solution requires plan digitization or Melvin confirming counts manually
  - Cannot fix without knowing plan density

- [ ] **#7 NEEDS MELVIN — B1/W1/S1/AB123/JH456/SP789 unknown codes**
  - Ask Melvin: are these real model numbers or placeholders?

- [ ] **#8 NEEDS MELVIN — CAD PDF LF = 0**
  - Whaleon, LHERT-SONG, SVR, Woodlane all show 0 LF (vector text not readable)
  - Options: DXF export from engineer, iBeam AI, tesseract OCR
  - Defer until Melvin confirms accuracy threshold

### Session 2026-06-15 — empty-result retry + 429 backoff + full run validation

- [x] **Empty-result retry ✅** — is_empty_result() in prompts.py; both Gemini + GPT-4o retry on {}
- [x] **Gemini 429 backoff ✅** — reads retry-after from error, sleeps, retries once
- [x] **TJI extraction confirmed ✅** — `11-7/8 TJI 210 @ 16" OC` extracted from LHERT SONG p59
- [x] **OCR timeout fix ✅** — raised from 900s → 1800s (12 pages × ~90s LF pass)
- [ ] **total_sqft classification variance** — p5 classified as schedules in one run but not another;
  causes Fix #2 wall stud quantities to disappear run-to-run. Root cause: Vision sees same page
  differently between batches.

**Hardware accuracy vs real Ganahl order (LHERT SONG):**
  CMST12: 43 vs 37 ✅close | CMST14: 33 vs 28 ✅close | LUS210: 0 vs 410 ❌
  HDU4: 2 vs 27 ❌ | A35: 4 vs 500 ❌ | DTT2Z: 1 vs 10 ❌
  p17/p19 are ARCHITECTURAL sheets (A-4.1a Letter Four) — no structural data, empty is correct
  S-2.1 = "Foundation and Basement Plans" — there is NO standalone 1F structural framing plan
  LUS210 = "TYP" callout on every joist — requires joist-grid counting, not text extraction
  A35 = similarly distributed as TYP throughout plans — same counting problem

### Newly surfaced gaps (2026-06-14 LHERT SONG run)

- [ ] **total_sqft = 0 on all CAD PDFs** — schedules pages (LHERT SONG p3/4/55/56/57, Whaleon)
  return empty results from text extraction. Building area not in a format the model reads.
  Fix: add explicit sqft extraction hint to schedules prompt, or scan for "BUILDING AREA" / "SQ FT" phrases.

- [ ] **Gemini silent empty on floor_framing plan pages** — p17/p19/p59 on LHERT SONG return
  result keys=[] (empty dict, not refusal). No joists, beams, or hardware extracted at all.
  Root cause unknown — may be rendering resolution, page complexity, or Gemini capacity.
  Fix: investigate render scale for Gemini calls; try retry with simplified prompt (same pattern as
  GPT-4o refusal retry already in place).

## Session 2026-06-15 (afternoon) — Phase 3 Rate Sheet + Security Fix + Flow Testing

- [x] **Phase 3 rate sheet ✅** — DB model (rate_sheets), migration 002, GET/PUT /api/rates,
  cost_estimate.py (quantities × rates → line items), PDF cost section, /settings/rates UI,
  dashboard nav link. Validated: $21,671 estimate on mock LHERT SONG data.
- [x] **Security fix ✅** — REGISTER_SECRET not injected into Docker container; anyone could
  register. Fixed in docker-compose.yml. Wrong invite code now returns 403.
- [x] **Full flow test ✅** — All 8 routes verified, auth guard, rate isolation per user,
  cost section appears in live PDF download, empty rates → no cost section.
- [x] **Client update written** — 3-day breakdown sent to Melvin covering Phase 2 fixes,
  pipeline reliability, TJI extraction, rate sheet, and blocking items.

### Phase 3 — what's built vs remaining

**Built:**
- Rate sheet: storage, UI, API, PDF section ✅
- Labor cost estimate: quantities × user rates → line items + total ✅

**Remaining in Phase 3:**
- [ ] Equipment cost rates (crane, pump, scaffold) — add fields to rate sheet, ~1 hr
- [ ] Results page: show cost estimate inline (without downloading PDF) — ~1 hr
- [ ] Waste factors — formula-based, ~1 hr
- [ ] Construction schedule — blocked on production rates from Melvin
- [ ] Full procurement list (Ganahl format) — blocked on lumber piece counts

### Remaining — independent code work (no external dep)
- [ ] Results page cost summary inline — web UI, ~1 hr
- [ ] total_sqft variance — add sqft hint to schedules prompt, ~30 min
- [ ] General hardware noise — "ALUMINUM ANGLE", "NEOPRENE BAD" to blocklist, ~15 min

### Blocking Melvin from using today
1. OpenAI key has no credits — can't run pipeline himself
2. Gemini key on free tier (20 req/day) — needs paid tier for production

### Most valuable next step
Get Melvin into the app (credentials sent), have him fill rate sheet and review estimate (25).
His feedback on hardware model accuracy > more engineering right now.
