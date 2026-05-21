# Pipeline Research Findings

**Last Updated:** 2026-05-21  
**PDFs Tested:** 6 sample files from Melvin Guzman (6 complete ✅)

---

## 1. PDF Library Comparison

| Library | Memory Usage | Speed | Verdict |
|---|---|---|---|
| `pdfplumber` | ~2.6GB for 172MB PDF | Crashed / timed out on 50 pages | Unusable for large files |
| `pypdfium2` | Low (lazy page loading) | ~2s for 167 pages | **Use this** |

`pypdfium2` binds to Google's PDFium engine. Reads pages on demand, not entire file at once.  
**Decision:** `pypdfium2` replaces `pdfplumber` throughout the app.

---

## 2. Text Extraction Behavior (pypdfium2)

pypdfium2 reads pages in **column order**, not top-to-bottom. The title block (sheet number, title) lands **in the middle or end** of extracted text.

**Three title block patterns found so far:**

| Pattern | Format | Firms |
|---|---|---|
| BSPK format | Sheet number on its own line mid-text: `\r\nT0-400\r\n` | SVR (BSPK Design) |
| Landscape/Civil format | Sheet number at start of text: `"L0.1 GENERAL NOTES ..."` | L/C sheets within SVR |
| Aram Ark format | Sheet number at end of text: `"...A.A. S-2.0 1/4"=1'-0" FOUNDATION PLAN"` | Whaleon (Aram Ark SE) |
| BARAGHOUSH format | Sheet number before "REVISION CLOUD SCHEDULE": `"A-4.1 REVISION CLOUD SCHEDULE"` | BARAGHOUSH (architectural-only) |

---

## 3. Classification Results — All 6 PDFs

| PDF | Pages | Size | Relevant Found | Status |
|---|---|---|---|---|
| `SVR_80% CD Set` | 167 | 172MB | 27 | ✅ Extracted — 0 errors |
| `Whaleon Residence CD` | 73 | 79MB | 7 | ✅ Extracted — 0 errors |
| `BARAGHOUSH DD progress` | 17 | 7MB | 0 | ✅ Complete — architectural-only DD set, no structural sheets |
| `Paseo Miramar RTI` | 57 | 216MB | 37 | ✅ Complete — raster pipeline validated (see section 7) |
| `4248 Woodlane Court` | 60 | 144MB | 5 | ✅ Complete — architectural set + LA City SMF standard plan |
| `LHERT SONG CD Bid Set` | 64 | 35MB | 10 | ✅ Complete — 70 framing connections, concrete+lumber specs |

---

## 4. SVR 80% CD Set — Detailed Structure (167 pages)

| Page Range | Series | Content | Relevant |
|---|---|---|---|
| 1 | Cover | Sheet list, project info, rendering | Yes |
| 3–10 | T0-200→T0-304 | General notes, code diagrams, area calcs | Yes |
| 17–18 | T0-600/601 | Door + window schedules | Yes |
| 20–49 | L, C series | Landscape + civil plans | No |
| 50 | A1-100 | Architectural site plan | Yes |
| 55–57 | A2-200→202 | Reflected ceiling plans | Yes (specs only) |
| 125–126 | S0.1/S0.2 | Structural general notes | Yes |
| 127–128 | HDU14 | Simpson hold-down schedule | Yes |
| 129–137 | S2.00→S2.43 | Wood framing details | Yes |
| 138 | HDU2 | Simpson hold-down schedule | Yes |
| 140–167 | M, E, P series | Mechanical, electrical, plumbing | No |

**Critical gap:** No S1 sheets (foundation plan, framing plans) — this is an 80% set.

**SVR Extraction Results (run 6 — final):**
- 27 pages, 0 parse errors, all text method, ~$0.00
- Project: SAN VICENTE RESIDENCE, 12957 SAN VICENTE BLVD., LA CA, 13,717.74 sqft
- Structural engineer: MICHAEL ZAHN STRUCTURAL ENGINEERING
- Sheet list: 14 structural sheets correctly identified
- Nailing schedule: 11 entries, Lumber specs: 7 entries, Concrete specs: 17 entries
- Simpson hardware: 52 items, Framing details: 49 connection items

---

## 5. Whaleon Residence CD Set — Detailed Structure (73 pages)

| Page Range | Content | Relevant |
|---|---|---|
| 1 | Cover sheet — project info | No (text too sparse) |
| 2 | Sheet index — all sheets listed | No (not classified) |
| 3–66 | Architectural (A-series) | No (sheet# not in text layer) |
| 67 | S-1.0 Structural Notes | Yes |
| 68 | S-2.0 Foundation Plan | Yes |
| 69 | S-2.1 Framing Plan | Yes |
| 70 | S-3.0 Typical Details | Yes |
| 71 | S-3.1 Structural Details | Yes |
| 72 | S-4.0 Structural Details | Yes |
| 73 | S-4.1 Structural Details | Yes |

**This is a complete CD set** — has foundation plan and framing plan (unlike SVR 80% set).

**Whaleon Extraction Results (run 2 — final):**
- 7 pages, 0 parse errors, 6 Vision + 1 text, ~$0.07
- Project: WHALEON RESIDENCE, 364 E. PENTAGON ST. ALTADENA, CA 91001
- Foundation: F1 (24"×12") + F2 (36"×18") footings, #4 rebar @ 12", 5/8" anchor bolts @ 48", HD1×4 + HD2×2
- Simpson hardware: 12 items (H1, A35, H10, LUS26, H2.5A, HUCQ410, ABU88, HDU5/8/11)
- Framing connections: 9 entries (beam-to-post, drag straps, joist hangers, hold-downs)
- `linear_feet` and `concrete_cubic_yards` = 0 — dimensions are graphical in drawing, not labeled text

---

## 6. BARAGHOUSH DD Progress Set — Detailed Structure (17 pages)

**This is an architectural-only Design Development set — no structural sheets.**

| Page | Sheet | Content | Relevant |
|---|---|---|---|
| 1 | (none) | Site plan — no standard title block in text | No |
| 2 | A-4.1 | Basement floor plan | No (architectural) |
| 3 | A-4.2 | First floor plan | No |
| 4 | A-4.3 | Second floor plan | No |
| 5 | A-5.1 | Roof plan | No |
| 6–9 | A-6.0–A-6.3 | Elevations | No |
| 10–15 | A-7.0–A-7.1 | Building sections | No |
| 16 | A-8.0 | Door schedule + types | No |
| 17 | A-8.1 | Window schedule + types | No |

**Conclusion:** 0 relevant pages. Nothing to extract. DD sets are architect-only; structural engineering is not engaged at this stage.

**Key classifier fix from BARAGHOUSH:**
- Added Pattern 4: detects sheet number before "REVISION CLOUD SCHEDULE" at end of text
- Added `"A-"` to `SKIP_PREFIXES`: handles BARAGHOUSH-style `A-4.x` sheet numbering
- Patterns 3 and 4 now run before Pattern 1 to prevent false positives from drawing body labels

---

## 7. Paseo Miramar RTI Stamped Plans — Detailed Structure (57 pages)

**Project:** HUNT RESIDENCE — Fire Rebuild, 571 Paseo Miramar, Pacific Palisades, CA 90272  
**Architect:** RNA (Rocha Nue Associates or similar)  
**Structural engineer:** KOBE (visible on structural sheets)  
**Type:** RTI (Ready to Issue) permit bundle — multiple discipline packages combined into one PDF  
**All pages:** Raster/scanned — zero extractable text. Full Vision pipeline required.

| Page Range | Sheet Numbers | Content | Relevant |
|---|---|---|---|
| 1 | A0.0 | Cover sheet — project title, consultants | No |
| 2 | C1.1 | Topographic survey | No |
| 3 | A0.1 | LA County assessor info + pre-fire photos | No |
| 4–5 | A0.2, A1.0 | Site plans | No |
| 6–8 | A2.0–A2.2 | Floor plans + roof plan | No |
| 9–11 | A3.0–A3.2 | Elevations + 3D view | No |
| 12 | A4.0 | Building section | No |
| 13–15 | A4.1–A4.3 | Foundation details | Yes |
| 16 | A5.0 | Structural notes | Yes |
| 17–18 | A7.1–A7.2 | Structural details | Yes |
| 19–20 | (A0.0, A0.1) | Floor plans — different package | No |
| 21–28 | A1.0–A11.x, T04 | General notes / energy forms — may include Title 24 false positives | Verify |
| 29–32 | T-002, S-001–S-003 | General structural notes (different firm) | Yes |
| 33–34 | S11–S12 | Concrete retaining wall details, wall sections | Yes |
| 35 | S10 | Foundation plan | Yes |
| 36–40 | S1–S4 | Structural notes, foundation plan, details, wall sections | Yes |
| 41–43 | SD1.2–SD1.4 | Foundation details (KOBE) | Yes |
| 44 | SD2.0 | Framing details (KOBE) | Yes |
| 45–51 | S11–S14, S05–S07 | Structural details, shear transfer, steel connections (KOBE) | Yes |
| 52–56 | C-1–C-5 | Civil: site plan, grading, civil notes | No |
| 57 | A1.0 | Site plan | No |

**Extraction Results (run 1 — final):**
- 37 pages processed, ~34 min, estimated ~$1–2
- Project: HUNT RESIDENCE, 571 Paseo Miramar, Pacific Palisades, CA 90272
- Architect: RNA
- Structural engineer: KOBE
- Concrete: 2500 PSI footings/slab, 3000 PSI all other concrete
- Nailing: 8d common @ 6" edges / 12" field (walls + roof sheathing)
- Lumber: Douglas Fir-Larch No. 2+, APA rated plywood
- Sheet list: 12 KOBE structural sheets (S1–S12)
- Steel connections: WD BM-WF BM, steel beam-to-beam, WF moment connection, steel pipe column connections
- Hardware: A325 + A490 high-strength bolts
- Foundation plan dimensions: 0 (graphical plans — same gap as other firms)

**Known limitations for raster PDFs:**
- Page 36 (dense soils notes): too long for 8000 token limit — truncates/fails
- Foundation plan drawings (13–15, 35, 37–43): graphical, correctly return zeros
- Project info fields (address, engineer name): susceptible to Vision hallucination on raster — mitigated by prompt instruction
- Title 24 forms (page 28) and admin docs (24, 26) correctly return empty

**Raster pipeline architecture:** `test_pipeline_raster.py`
- Phase 1: Render all pages as 700px thumbnails, batch 4 per Vision call (`detail: low`) for classification
- Phase 2: Render structural pages at ~180 DPI for extraction (`detail: high`, 8000 max_tokens)
- `--classify-only` flag: run Phase 1 only, save JSON
- `--rerun-pages 32,36` flag: re-run specific pages from saved classification JSON (no re-classification)

---

## 8. Cross-Firm Title Block Formats

### BSPK Design (SVR) — Pattern 1
Sheet number on its own line mid-text:
```
...CITY DOCUMENTS\r\nT0-400\r\nRODNEY MESRIANI...
```
Sheet number: standalone line. Title: line immediately before.

### Landscape/Civil (within SVR) — Pattern 2
Sheet number at very start of text:
```
L0.1 GENERAL NOTES ...
```

### Aram Ark Structural Engineer (Whaleon) — Pattern 3
Sheet number near end of text after engineer initials:
```
...02/25/2026 A.A. S-2.0 1/4"=1'-0" FOUNDATION PLAN
```
Format: `A.A. [SHEET_NO] [SCALE] [TITLE]`

### ADEVARC (Whaleon architectural pages)
Architectural pages 1–66: sheet number NOT in text layer — only in graphical title block.
Sheet index on page 2 has all sheets but runs together without clean line breaks.

### BARAGHOUSH (DD progress) — Pattern 4
Sheet number appears immediately before "REVISION CLOUD SCHEDULE" near end of text:
```
...A-4.1 REVISION CLOUD SCHEDULE\r\nREV. MARK DESCRIPTION DATE COMMENTS
```
Sheet number format: `[LETTER]-[DIGIT].[DIGIT]` (e.g., `A-4.1`, `A-7.0`).  
All sheets are A-series architectural. This is a DD set — no structural sheets present.  
Pattern 4 runs before Pattern 1 to prevent false positives from skylight labels (`S1`, `S2`) in window schedules.

### Paseo Miramar RTI Stamped Plans
Zero text on all 57 pages — fully raster/scanned PDF.

### Letter Four (LHERT SONG)
Sheet number embedded in paragraph alongside project metadata — format unknown.

---

## 7. Routing Logic (current — test_pipeline.py)

Pages are routed to text extraction or Vision based on:

```python
TEXT_HEAVY_MIN_CHARS = 2000
VISION_ONLY_CATEGORIES = {"floor_framing", "roof_framing", "foundation"}

def is_text_heavy(text, category):
    if category in VISION_ONLY_CATEGORIES:
        return False          # always Vision
    return len(text.strip()) > TEXT_HEAVY_MIN_CHARS
```

**Why 2000 chars threshold:**
- SVR/Zahn structural pages: 3000–6000 chars → text extraction works well
- Whaleon/Aram Ark structural pages: 640–715 chars → Vision needed
- 2000 cleanly separates the two

**Category routing summary:**

| Category | Routing | Reason |
|---|---|---|
| `schedules` | text if >2000 chars, else Vision | T0/S0 notes have lots of text |
| `framing_details` | text if >2000 chars, else Vision | SVR: text-heavy; Whaleon: graphical |
| `wall_framing` | text always | A2 RCP pages: Vision hallucinates |
| `foundation` | Vision always | Foundation plans are graphical |
| `floor_framing` | Vision always | Floor plans are graphical |
| `roof_framing` | Vision always | Roof plans are graphical |

---

## 8. Sheet Number Classification Config

```python
SHEET_NUMBER_MAP = {
    # SVR / BSPK Design / Zahn SE
    "S0":   "schedules",
    "S1":   None,              # classified by title (foundation/framing/roof)
    "S2":   "framing_details",
    "T0-1": "schedules",
    "T0-2": "schedules",
    "T0-3": "schedules",
    "T0-6": "schedules",
    "A1":   "schedules",
    "A2":   "wall_framing",
    "HD":   "schedules",
    # Whaleon / Aram Ark SE
    "S-1":  "schedules",
    "S-2":  None,              # classified by title (foundation/framing)
    "S-3":  "framing_details",
    "S-4":  "framing_details",
}
SKIP_PREFIXES = ("L", "M", "E", "P", "C", "A3", "A4", "A5", "A6", "A-", "T0-4", "T0-5")
```

Note: `"F" → "foundation"` removed — in SVR/Zahn drawings `F1`, `F2` are detail figure numbers.  
Note: `"A-"` added to SKIP_PREFIXES — handles BARAGHOUSH-style architectural sheets (`A-4.x`, `A-5.x` etc.).

---

## 8. Woodlane Court (4248 Woodlane Court — All Plans.pdf)

- **File:** `4248 Woodlane Court - All Plans.pdf` (60 pages, 144MB)
- **Project:** WLV 1 DEVELOPMENT RESIDENCE, 4248 WOODLANE COURT, WESTLAKE VILLAGE, CA 91362
- **Architect:** ARC Design Group (R E S I D E N T I A L DESIGN GROUP)
- **SE:** JT Engineering Associates, Inc., 107 N Reino Road, Suite #153, Newbury Park, CA 91320
- **Result:** 5 pages, 0 errors, ~$0.06
- **Pipeline:** `test_pipeline.py`

### Pages extracted
| Page | Sheet | Category | Result |
|---|---|---|---|
| 9 | A1.2 | schedules | Project info + SE ✅ (text mode) |
| 10 | A1.3 | schedules | Project info + notes ✅ (text mode) |
| 11 | A2.1 | wall_framing | Zeros only — graphical floor plan ✅ |
| 12 | A2.2 | wall_framing | Zeros only — graphical floor plan ✅ |
| 39 | T1 | framing_details | 4 SMF CJP weld connection types ✅ (text) |

### Key findings
- **No structural S sheets** — PDF is architectural permit set only. Structural package is a separate submission. No lumber, concrete, nailing, or foundation data expected.
- **T1 sheet** is the LA City Steel Moment Frame Standard Quality Assurance Plan — confirms steel moment frame construction type for this project. Connection types: CJP groove weld, web doubler plate, weld access hole, plug welding.
- **Pages 37-38** (LA City SMF standard plan sheets 1-2, 28K+11K chars) classified as `unknown` — no recognizable sheet number. These are standard city plan sheets, not project-specific. Not extracted.

### Fixes applied this run
1. **Schedules → text routing**: `schedules` category now always uses text extraction when >100 chars. Vision was reading general notes content instead of title block (caused missing SE field).
2. **framing_details `connections` aggregation**: Added `data.get("connections")` alongside `data.get("hardware")` in aggregation loop — T1 sheet returns `connections` not `hardware`.
3. **simpson_hardware filter**: Only framing_details items with `model` key are added to `simpson_hardware` — prevents SMF connection descriptions from polluting the hardware list.

---

## 9. Extraction Gaps — What We Deliver vs. What the Spec Requires

### What the pipeline delivers reliably ✅

| Field | Quality | Notes |
|---|---|---|
| Project info (name, address, architect, SE) | Excellent | All 6 PDFs correct |
| Concrete specs (PSI, mix design) | Excellent | Text layer |
| Lumber specs (species, grade, LVL/LSL design values) | Excellent | Text layer |
| Nailing schedules | Good | When present in text (SVR: 11 entries) |
| Simpson hardware model numbers | Good | Quantities often 0 |
| Connection/framing details | Good | LHERT SONG: 70 items |
| Sheet lists | Good | |

### What the spec requires that we can't reliably deliver ❌

The design spec output schema (`analysis_results.raw_json`) includes these fields that are not extractable from the PDF text layer:

| Field | Root Cause |
|---|---|
| `concrete_cubic_yards` | Requires footing dimensions × linear feet — lives in graphical drawing geometry, not text |
| `rebar_lf`, `rebar_qty` | Same — graphical |
| `sheathing_sheets` | Never appears in text layer |
| Lumber piece counts (qty of 2x10s, beams, etc.) | Requires counting members from framing plan drawings |
| `labor_estimate` | Not in PDFs — must be calculated from quantities |
| `equipment_costs` | Not in PDFs |
| `construction_schedule` | Not in PDFs |

**The core gap:** The spec wants a quantity takeoff (how much to order). Quantities live in drawing geometry (dimension lines, layout grids). The pipeline reads the spec/notes text layer very well but can't reliably extract graphical dimensions.

**Vision estimation caveat:** Vision can estimate quantities from plan images (LHERT SONG returned 20 CY, 150 LF) but these are plausible guesses, not verified measurements. They vary in accuracy and cannot be trusted for ordering.

### Scope clarification needed with Melvin before building web app

Two valid directions:
1. **Spec + hardware list** — Deliver material specifications, hardware schedules, and connection details. Mark quantity fields (CY, LF, piece counts) as "requires field measurement." This is what the pipeline actually produces accurately.
2. **Add dimension extraction** — Targeted Vision pass on foundation/framing plans specifically reading dimension strings. Improves CY/LF accuracy but still not 100% reliable.

Question for Melvin: does he expect to enter plan dimensions himself and get specs + hardware from the AI, or does he expect the AI to generate the full takeoff numbers from the drawings?

### Other known gaps (per-PDF)

| Gap | Affected | Root Cause |
|---|---|---|
| `linear_feet` = 0 for footings | Whaleon | Dimensions graphical, not text |
| Wall `linear_feet` = 0 | SVR | RCP pages have no wall dimension labels |
| 66 unknown pages | Whaleon | A-series sheet# only in graphical title block |
| No S1 structural sheets | SVR, Woodlane | 80% set / arch-only PDF |
| Foundation plan parse_error | LHERT SONG p60 | Vision refused on complex roof framing plan |

---

## 9b. LHERT SONG CD Bid Set (2025_09-30 LHERT SONG CD Bid Set.pdf)

- **File:** `2025_09-30 LHERT SONG CD Bid Set.pdf` (64 pages, 35MB)
- **Project:** Lhert-Song, 3333 Cabrillo Blvd, Los Angeles, CA 90066
- **Architect:** Letter Four, Inc. | **SE:** Ashley & Vance Engineering Inc. (Sean Galbreath, SE #5653)
- **Result:** 10 pages, 0 errors, 2.0 min, ~$0.28
- **Pipeline:** `test_pipeline.py`

### Pages extracted
| Page | Sheet | Category | Method | Result |
|---|---|---|---|---|
| 55 | S-1.1 | schedules | text | Project info + sheet list + concrete specs ✅ |
| 56 | S-1.2 | schedules | text | Lumber specs (GLB, LVL, LSL, PSL) + concrete 3000 PSI ✅ |
| 57 | S-1.3 | schedules | text | Special inspections notes ✅ |
| 58 | S-2.1 | foundation | vision | Footings, rebar, hold-downs (⚠️ quantities likely estimated) |
| 59 | S-2.2 | floor_framing | vision | 2x10 joists, LVL beams (⚠️ quantities likely estimated) |
| 60 | S-2.3 | roof_framing | vision | ⚠️ parse_error — Vision refused on complex framing plan |
| 61 | S-3.1 | framing_details | text | 6 connections, 13 hardware items (HDU2-HDU14, SSTB rods) ✅ |
| 62 | S-3.2 | framing_details | text | 17 shear transfer connections, 7 hardware items ✅ |
| 63 | S-3.3 | framing_details | text | 17 strap/drag connections, 10 hardware items (CS14, CMSTC16) ✅ |
| 64 | S-3.4 | framing_details | text | 4 connections, 6 hardware items (MSTA18, HDU8) ✅ |

### Key findings
- **70 framing connection items** — best detail extraction across all 6 PDFs
- **Concrete specs table**: 2500/3000/4000/5000/6000 PSI rebar development lengths (#3–#8)
- **Lumber specs**: GLB, LVL (E=2000 ksi), LSL (E=1550 ksi), PSL (E=2200 ksi) design values
- **Hardware**: HDU2/4/5/8/11/14, HD19, SSTB16/20/24/28, SB1x30, CS14, CMSTC16, CMST14/12, MSTA18/24/30, A35, LTP4, DTT2Z, WSWH-TP
- **Foundation plan quantities** (20 CY, 150 LF continuous, 30 LF isolated) — estimated by Vision on graphical drawing, same limitation as Whaleon
- **54 unknown pages** — all Letter Four architectural sheets (A-series), no sheet number in text layer

### Fixes applied — Pattern 5 (Ashley & Vance)
The A&V title block `AV JOB:` is unique. New Pattern 5 anchors to this marker and captures the title lines + sheet number. **Run first** (before Pattern 1) to prevent false positives:

```python
if 'AV JOB:' in text:
    match5 = re.search(r'AV JOB:\r?\n((?:[^\n\r]*\r?\n){1,4})(S-\d[\d.]*)', text)
    if match5:
        sheet_no = match5.group(2).upper()
        title = match5.group(1).replace('\r\n', ' ').replace('\n', ' ').strip().lower()
        return sheet_no, title
```

**Why Pattern 1 fails:** `AV JOB:` title block is in the right column. Column-order reading puts hardware callouts (`CC66`, `CS14`, `HDU2`) BEFORE the title block. Pattern 1 (`[A-Z]{1,3}\d[\d.\-]*\d?`) matches these callouts as false-positive sheet numbers. Pattern 5 avoids this by anchoring to `AV JOB:`.

---

## 10. Run History

### SVR 80% CD Set

| Run | Key Change | Result |
|---|---|---|
| 1 | pdfplumber, keyword classifier | OOM crash |
| 2 | pypdfium2, sheet-number classifier, DPI=150 | Many "unable to extract" |
| 3 | DPI=250, neutral prompt, score-based address trust | Hallucinated addresses |
| 4 | Text-heavy detection (>500 chars), max_tokens 4000→8000 | 0 Vision calls; pages 3,4 still parse_error |
| 5 | wall_framing → VISION_ONLY; Vision max_tokens=8000 | Vision refused; pages 56,57 truncated |
| 6 | wall_framing out of VISION_ONLY; project merge by field; F→foundation removed | **0 errors ✅** |

### Whaleon Residence CD Set

| Run | Key Change | Result |
|---|---|---|
| 1 | First run — Pattern 3 added; S-1/S-2/S-3/S-4 mappings | Structural pages found; framing details empty (Vision threshold too low) |
| 2 | TEXT_HEAVY_MIN_CHARS 500→2000; Whaleon pages flip to Vision | **0 errors ✅ Real foundation + hardware data** |

---

## 11. Test Scripts

| File | Purpose |
|---|---|
| `scripts/test_pipeline/test_pipeline.py` | Main pipeline — current working version |
| `scripts/test_pipeline/test_classify.py` | Fast standalone classification (no API) |
| `scripts/test_pipeline/classify_all.py` | Classification across all 6 PDFs |
| `scripts/test_pipeline/debug_text.py` | Print raw pypdfium2 text for specific pages |
| `scripts/test_pipeline/debug_unknown.py` | Inspect unknown pages |
| `scripts/test_pipeline/debug_formats.py` | Compare title block formats across PDFs |
| `scripts/test_pipeline/test_pipeline_raster.py` | Two-phase raster pipeline: batch thumbnail classification + Vision extraction |

---

## 12. Next Steps (in order)

1. ~~BARAGHOUSH DD~~ — ✅ done, architectural-only DD set
2. ~~**Paseo Miramar**~~ — ✅ done, raster pipeline validated
3. ~~**Woodlane Court**~~ — ✅ done, architectural set + LA City SMF standard plan
4. ~~**LHERT SONG CD**~~ — ✅ done, 70 framing connections, concrete+lumber specs
5. **Implementation plan** — invoke writing-plans skill ← NEXT
5. **Foundation `linear_feet`** — add targeted dimension-reading prompt to Vision extraction
6. **Cover sheet index parser** — for architectural pages in Whaleon + other firms
7. **Complete S1 set** — test foundation/framing plan quantity extraction
8. **Implementation plan** — invoke writing-plans skill
9. **Build web app** — FastAPI + Next.js + PostgreSQL + Docker
