# Phase 2 Engineering Plan — Procurement List Generation

**Created:** 2026-06-13
**Goal:** Produce a preliminary procurement list in Ganahl Lumber format that Melvin can review and submit
**Reference:** `memory/procurement_format.md` — real Ganahl order EST618017 ($125k, LHERT-SONG)

---

## The Engineering Problem

Melvin needs a list like this:
```
Qty  | Size       | Length | Description         | Notes
195  | 2x6        | 10ft   | #2 & BTR DF S4S     | 1st Floor walls
380  | LUS210     | —      | Simpson joist hanger| 1st Floor framing
86   | 4x8 23/32  | —      | CD T&G PLY subfloor | 1st Floor
```

We currently produce: specs (grades, sizes) + hardware models — but NOT quantities.

**The fundamental constraint:**
Counting individual members from plan images requires plan digitization (Bluebeam territory).
AI vision can read text/schedules but cannot count every joist on a framing plan.

**The engineering solution:**
Use extracted specs + floor area + standard construction factors to generate a preliminary
quantity estimate. Mark everything as "preliminary — verify before ordering."
This is how estimators work when doing conceptual takeoffs without full plan access.

---

## Priority Order

```
Priority 1 — Hardware Schedule Extraction (HIGH VALUE, ACHIEVABLE NOW)
Priority 2 — Phase-Based Output Reorganization (HIGH VALUE, MEDIUM EFFORT)
Priority 3 — Quantity Estimation Module (MEDIUM VALUE, MEDIUM EFFORT)
Priority 4 — CAD PDF improvements (ONGOING)
```

---

## Priority 1: Hardware Schedule Extraction

**What:** Read hold-down, strap, and joist hanger schedules directly from plan pages
**Why:** Schedule tables are readable by OCR — gives exact quantities, not estimates
**Expected accuracy:** 85-95%

**Evidence:** Paseo Miramar p35 has GRADE BEAM SCHEDULE (readable by OCR):
- Hold-downs: HDU4×13, HDU8×14, HDUE17×2
- Simpson strap schedule: CMSTC16×2, CMST14×2, CMST12×5
- This is how the real order gets HDU4=13 (vs our ~3 from details)

Floor/roof framing pages have joist hanger schedules:
- ITS2.06/11.88 × 300 (I-joist hangers)
- LUS210 × 380
- These come from schedule tables, not individual callouts

**Implementation steps:**
1. In `ocr.py`: after extracting all text from a page, detect schedule table headers
   - Look for: "SCHEDULE", "MARK", "MODEL", "QTY", "SYM.", "SIMPSON"
   - Parse rows: SYM | MODEL | QTY pattern
2. Return as `hardware_schedule: [{"model": "HDU4-SDS2.5", "qty": 13}]`
3. In `aggregate.py`: merge schedule hardware with Gemini-extracted hardware
   - Schedule qty takes priority over Gemini qty (more accurate)
4. In `runner.py`: add schedule parsing pass after main extraction

**Files to change:** `ocr.py`, `aggregate.py`, `runner.py`

---

## Priority 2: Phase-Based Output Reorganization

**What:** Reorganize output from type-based to construction-phase-based
**Why:** Melvin thinks by floor: Material → 1st Floor → 2nd Floor → Ceiling
**Impact:** Makes the report directly usable as a Ganahl order starting point

**Target output structure:**
```
Section 1: FOUNDATION
  Grade Beam Schedule (type, W×D, top R/F, bot R/F, stirrups)
  Quantities: total LF*, CY*
  Hardware: hold-downs, anchor bolts (from schedule)

Section 2: FLOOR FRAMING
  Lumber: joists (size/spacing), beams (size/span), posts
  Plywood: subfloor sheets (estimated from floor area)
  Hardware: joist hangers, post caps (from schedule)

Section 3: WALL FRAMING
  Lumber: studs (size/spacing), plates, headers
  Sheathing: plywood sheets (estimated)
  Hardware: straps, holdowns (from schedule)

Section 4: ROOF FRAMING
  Lumber: rafters/beams (size/spacing)
  Sheathing: roof panels (estimated)
  Hardware: hurricane ties, connectors (from schedule)

Section 5: HARDWARE SUMMARY (consolidated, all phases)
  All Simpson hardware with quantities
```

**Files to change:** `aggregate.py` (new phase structure), `generator.py` (new PDF sections)

---

## Priority 3: Quantity Estimation Module

**What:** Use extracted specs + floor area + standard factors → estimated piece counts
**Why:** Gets from "2x6 @ 16"OC" to "~195 pcs 2x6x10" — 50-70% accurate
**Mark all:** `estimated: true` — preliminary only

**Standard construction factors (CA residential):**
```python
FACTORS = {
    "studs_per_lf":      1.0 / 1.33 * 2.2,  # 16"OC, double top plate, 10% waste
    "joists_per_sqft":   1.0,                # per foot of spacing
    "plywood_subfloor":  1.0 / 32 * 1.1,    # 4x8=32sqft, 10% waste
    "wall_sheathing":    1.0 / 32 * 1.1,
    "roof_sheathing":    1.0 / 32 * 1.1,
}
```

**Inputs available:**
- `total_sqft` from title block (extracted by Gemini) ✅
- Stud/joist sizes + spacing from framing plans (extracted by Gemini) ✅
- Wall LF from OCR (partial) or estimated from sqrt(sqft) × perimeter factor

**New file:** `app/backend/app/pipeline/quantities.py`

```python
def estimate_quantities(framing_data: dict, total_sqft: int) -> dict:
    """
    Given extracted framing specs and floor area, estimate lumber piece counts.
    Returns quantities marked estimated=True. 50-70% accuracy.
    """
```

---

## Priority 4: CAD PDF Accuracy (Ongoing)

**CAD PDFs (Whaleon, LHERT-SONG, Woodlane, SVR):**
- Dimension text is vector-rendered → OCR can't read it
- Options:
  - `sudo apt install tesseract-ocr` + render to image (test first)
  - DXF export from structural engineer (near-perfect, needs engineer cooperation)
  - iBeam AI specialist service ($150-500/job, 90-98% accuracy)
- Defer until Track 1 priorities are working

**Scanned PDFs (Paseo Miramar):**
- OCR already working ✅
- Foundation LF: 128.6 ft confirmed
- Need to test floor/wall framing pages for schedule tables

---

## Success Criteria

When Phase 2 is complete, Melvin should be able to:
1. Upload a PDF plan set
2. Download a preliminary procurement list organized by phase
3. Share it with Ganahl as a starting point
4. Adjust quantities from his experience
5. 70-80% of lines match his final order

**Not the goal:** Replace Melvin's judgment. Time-saving starting point only.

---

## Files Affected

| File | Change |
|---|---|
| `app/backend/app/pipeline/ocr.py` | Add schedule table parser |
| `app/backend/app/pipeline/quantities.py` | NEW — quantity estimator |
| `app/backend/app/pipeline/aggregate.py` | Phase-based structure + schedule merge |
| `app/backend/app/pipeline/prompts.py` | Ask Gemini for schedule data |
| `app/backend/app/report/generator.py` | Phase-based PDF sections |

---

## Current State (as of 2026-06-13)

**Done:**
- Gemini extracts: hardware models, footing types + rebar, lumber specs ✅
- PaddleOCR extracts: total LF from scanned foundation plans ✅
- PDF shows: foundation schedule with rebar, hardware, connections ✅

**Not done:**
- Hardware schedule tables not parsed (only individual mentions)
- No lumber piece counts
- No plywood sheet counts
- Output organized by data type, not by floor
- Quantities not organized in Ganahl format
