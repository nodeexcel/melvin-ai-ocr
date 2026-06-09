# Project TODO

**Project:** AI Construction Estimator — Mel's Builders Pro Systems  
**Last Updated:** 2026-06-08

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

- [x] **PaddleOCR investigation (installed, runtime incompatible)**
  - Installed `paddleocr-3.6.0` + `paddlepaddle-3.3.1`
  - Runtime error: `NotImplementedError: ConvertPirAttribute2RuntimeAttribute` — incompatible with Python 3.13 / this hardware
  - DO NOT add to `requirements.txt` — not usable
  - Uninstall from venv before next Docker rebuild to avoid bloating image

- [ ] **Phase 2 LF extraction — NEXT STEPS (clear path forward)**
  - **For scanned PDFs (Paseo Miramar):** Gemini vision OCR on full-res rendered page IS the right approach — scanned = raster image, Gemini can read all text including dimension callouts
    - Tested approach: render page → send to Gemini with focused "read dimension callouts" prompt
    - BLOCKED: free tier Gemini keys = 20 req/day, exhausted during testing
    - Fix: need paid Gemini account (even $5 covers weeks). OR wait for daily quota reset + test immediately
  - **For CAD PDFs (Whaleon, LHERT SONG, Woodlane, SVR):** 
    - Option A: `sudo apt install tesseract-ocr` → render page image → pytesseract OCR on drawing annotations
    - Option B: DXF export from engineer — ezdxf reads CAD layers precisely (~99% accuracy)
    - Option C: iBeam AI specialist service — outsource entirely ($150-500/job)
  - **Decision pending:** test Gemini OCR on Paseo Miramar first (easiest path), evaluate numbers, then decide on CAD PDF approach

- [ ] **Gemini quota blocker — must resolve before testing**
  - Both Melvin's key and dev key exhausted (20 req/day free tier)
  - Solution: paid Gemini billing at aistudio.google.com (any amount) OR daily reset
  - DO NOT send Melvin message about Phase 2 accuracy until we've tested and have actual LF numbers

- [ ] **Quantity takeoff — Phase 2 (unblocked when quota resolved)**
  - Architecture is ready (dimension pass, estimated flag, PDF display all built)
  - Just need a working Gemini key + test Paseo Miramar foundation plan

- [ ] **Derived outputs — Phase 3:** Waste factors, procurement list, labor estimate (RSMeans), equipment costs, construction schedule
- [ ] Cover sheet index parser for A-series architectural page routing
