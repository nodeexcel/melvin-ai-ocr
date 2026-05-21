# Project TODO

**Project:** AI Construction Estimator — Mel's Builders Pro Systems  
**Last Updated:** 2026-05-21

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

## App Build ✅ COMPLETE (2026-05-21) — PDF report fully verified

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

## Blocked / Waiting

- None — all known gaps resolved ✅

## V2 Ideas (future)

- [x] ~~**Fix project info extraction**~~ — ✅ confirmed NOT broken. Data correctly extracted at `raw_json["project"]`. Earlier diagnosis used wrong lookup path. See `docs/pipeline-findings.md` Section 10.
- [ ] Full quantity takeoff module (CY, LF, piece counts) — needs R&D, Vision-based geometry reading
- [ ] Register endpoint for self-service user creation
- [ ] Raster PDF support in web app (currently digital PDFs only)
- [ ] Cover sheet index parser for A-series architectural page routing
