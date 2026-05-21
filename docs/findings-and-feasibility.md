# Pipeline Findings, Feasibility Assessment & Client Questions

**Date:** 2026-05-21  
**Project:** AI Construction Estimator — Mel's Builders Pro Systems  
**Status:** Pipeline validated on all 6 PDFs. Scope clarification needed before web app build.

---

## 1. What We Built and Validated

Two extraction pipelines, tested against 6 real PDF plan sets from 5 different structural engineering firms.

### Pipeline 1 — Digital PDFs (`test_pipeline.py`)
For PDFs with a machine-readable text layer (most modern plan sets).

- **Phase 1 — Classify:** Extract text from every page using pypdfium2. Identify sheet number from title block using firm-specific patterns. Map sheet number → category (schedules, foundation, framing, details, skip).
- **Phase 2 — Extract:** Text-heavy pages (>2000 chars) → GPT-4o text mode. Sparse pages + framing plans → GPT-4o Vision on rendered page image.
- **Phase 3 — Aggregate:** Merge all page-level results into a single structured JSON.

### Pipeline 2 — Raster/Scanned PDFs (`test_pipeline_raster.py`)
For PDFs with zero text (stamped/scanned plans).

- **Phase 1 — Classify:** Render all pages as low-res thumbnails (700px, JPEG), send 4 per Vision call for cheap batch classification.
- **Phase 2 — Extract:** Render structural pages at ~180 DPI, run full Vision extraction.

### Firms Covered (5 title block patterns)

| Pattern | Firm | Format |
|---|---|---|
| Pattern 1 | BSPK Design / Michael Zahn SE | Sheet# on its own line mid-text |
| Pattern 2 | Landscape/Civil sheets | Sheet# at start of text |
| Pattern 3 | Aram Ark SE (Whaleon) | `A.A. S-2.0 SCALE TITLE` at end |
| Pattern 4 | BARAGHOUSH architect | Sheet# before `REVISION CLOUD SCHEDULE` |
| Pattern 5 | Ashley & Vance Engineering | `AV JOB:` → title lines → sheet# |

---

## 2. Test Results — All 6 PDFs

| PDF | Pages | Structural Found | Cost | Result |
|---|---|---|---|---|
| SVR 80% CD Set | 167 | 27 | ~$0.00 | 11 nailing, 7 lumber, 17 concrete, 52 Simpson, 49 connections ✅ |
| Whaleon Residence CD | 73 | 7 | ~$0.07 | Foundation footings, rebar, 12 Simpson, 9 connections ✅ |
| BARAGHOUSH DD | 17 | 0 | $0.00 | Architectural-only DD set — no structural sheets ✅ |
| Paseo Miramar RTI | 57 | 37 | — | Raster pipeline — concrete, nailing, steel connections ✅ |
| 4248 Woodlane Court | 60 | 5 | ~$0.06 | Arch permit set only — SE extracted, 4 SMF connections ✅ |
| LHERT SONG CD | 64 | 10 | ~$0.28 | 70 framing connections, concrete/lumber specs ✅ |

---

## 3. What the Pipeline Delivers Reliably

These fields are extracted accurately and consistently across all PDF types:

| Data | Source | Notes |
|---|---|---|
| Project name, address | Title block text | All 6 PDFs correct |
| Architect, structural engineer | Title block text | All 6 PDFs correct |
| Concrete PSI specs | Structural notes text | 2500–5000 PSI found across PDFs |
| Rebar grade + spacing specs | Structural notes text | Bar size, development lengths |
| Lumber species + grade | Structural specs text | DF-L No. 2, LVL/LSL/PSL design values |
| Nailing schedules | Structural notes text | 11 entries in SVR |
| Simpson hardware model numbers | Detail sheets + schedules | Models correct; quantities variable |
| Framing connection types | Detail sheets text | 70 in LHERT SONG, 49 in SVR |
| Sheet lists | Title sheet text | Complete structural sheet index |
| Special inspections requirements | S-1.3 type sheets | Concrete, welding, hold-down inspection notes |

**What this gives Melvin:** He knows exactly what grade of materials to use, which Simpson connectors are specified, what concrete strength is required, and what the inspector will be checking. This is sufficient for bidding and procurement planning.

---

## 4. What We Cannot Reliably Deliver

These fields appear in the design spec output schema but cannot be extracted from PDF documents:

### 4a. Quantities that live in graphical geometry

| Field | Why We Can't Get It |
|---|---|
| `concrete_cubic_yards` | Calculated from footing dimensions × linear feet. Dimensions are drawn lines on the plan, not text. |
| `rebar_lf` / `rebar_qty` | Same — requires reading the foundation plan layout. |
| `sheathing_sheets` | Square footage of wall/roof area. Never printed as text in structural drawings. |
| Lumber piece counts (# of 2x10s, beams) | Requires counting members from framing plan drawings. |
| Footing linear feet | Foundation plan dimensions are graphical. |
| Wall linear feet | Requires reading architectural floor plan dimensions. |

**Why Vision doesn't solve this:** GPT-4o Vision can read what's visually on a page, but dimensional measurements on structural drawings require precise reading of dimension strings at specific scales. Vision gives plausible-sounding estimates (e.g., "20 CY") but these are guesses, not measurements. They cannot be used for ordering without verification.

### 4b. Fields not in PDFs at all

| Field | What It Requires |
|---|---|
| `labor_estimate` | Industry rules of thumb applied to quantities. Quantities must be known first. |
| `equipment_costs` | Project-specific — depends on site conditions, crew size, rental rates. |
| `construction_schedule` | Sequencing logic + crew productivity rates. Not derivable from plans alone. |
| `procurement_list` | Can be generated from extracted specs + hardware, but quantities still missing. |

---

## 5. What Is Achievable — Two Paths

### Path A — Spec + Hardware Report (buildable now, reliable)

Deliver a structured report containing:
- Project identification (name, address, architect, SE)
- Material specifications (concrete PSI, lumber species/grade)
- Complete Simpson hardware schedule (models specified)
- Framing connection details (what connection type goes where)
- Nailing schedule
- Special inspection requirements
- Structural sheet list

**Melvin enters quantities** (CY, LF, piece counts) manually from his own field measurement or takeoff. The app gives him everything else.

**Accuracy:** High. Everything comes from the text layer or verified spec sheets.  
**Build timeline:** Straightforward — pipeline is proven, web app is the remaining work.

---

### Path B — Full Quantity Takeoff (requires additional engineering, accuracy not guaranteed)

To extract quantities from graphical drawings, additional work is needed:

| Requirement | Approach | Confidence |
|---|---|---|
| Footing linear feet | Targeted Vision pass on foundation plan: "read every dimension string and footing callout" | Medium — works on clean drawings, fails on dense/small-scale plans |
| Concrete CY | Calculate from footing schedule (type × width × depth × LF) once LF is extracted | Medium — depends on LF accuracy |
| Lumber counts | Vision pass on framing plan: "list every joist, beam, post with size and count" | Low — framing plans are complex; counts are error-prone |
| Sheathing area | Vision pass on floor/roof plan: "estimate total sheathed area in sq ft" | Low — estimate only |
| Labor estimate | Formula-based: apply crew-hour factors to extracted quantities | Medium — once quantities are reliable |
| Equipment costs | Not feasible from PDFs alone — site-specific |
| Construction schedule | Partial — phase sequencing can be generated from sheet list + scope |

**Accuracy:** Variable. Foundation dimensions are often readable. Lumber counts on complex framing plans are unreliable.  
**Build timeline:** 4–6 additional weeks of pipeline R&D plus evaluation against a larger PDF test set.  
**Risk:** Quantities may look plausible but be wrong. Melvin could over- or under-order materials.

---

## 6. Recommendation

**Build Path A for V1.** It is reliable, buildable now, and genuinely useful for bidding. Mark the quantity fields clearly in the UI as "requires field measurement" so Melvin knows which numbers to enter himself.

Add a manual entry mode to the results screen where Melvin can fill in the quantity fields (CY, LF, piece counts). Once entered, the app calculates the full procurement list and cost estimate.

**Path B can be explored in V2** after V1 is in use and we have feedback on which quantities Melvin actually needs the AI to generate vs. which he prefers to enter himself.

---

## 7. Known Technical Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| Architectural pages (A-series) not classified | 54–66 pages per PDF remain "unknown" — floor plans, elevations, sections are not read | Cover sheet index parser (future) |
| Raster PDFs have lower extraction quality | Paseo Miramar: some pages truncated at 8000 token limit | Accepted for V1; retry logic for V2 |
| Dense spec pages (soils, geotech) can exceed token limit | parse_error on 1–2 pages per raster PDF | Accepted limitation — these pages rarely contain structural specs |
| Vision refusals on complex graphical pages | 1–2 parse_errors per PDF (e.g., roof framing plan p60 in LHERT SONG) | Accepted — these are graphical-only pages with no spec text |
| Hardware quantities often = 0 | Model numbers extracted but count is 0 when qty not explicitly stated in detail | Schedule pages (HDU schedule, WSWH schedule) provide counts where present |
| Foundation plan quantities are Vision-estimated | 20 CY, 150 LF etc. from LHERT SONG are plausible guesses not measurements | Flag as `estimated: true` per Rule 5 in CLAUDE.md |
| DD sets (design development) have no structural data | BARAGHOUSH returned 0 relevant pages — structural engineering not yet engaged at DD stage | Detect and inform user: "This appears to be a DD set — structural drawings not yet included" |

---

## 8. Questions for Melvin (Before Building)

These need answers before writing the implementation plan.

### 8.1 — Quantity takeoff scope (CRITICAL)
The pipeline extracts material specifications and hardware schedules reliably, but cannot reliably extract quantities (concrete CY, lumber piece counts, sheathing area) from graphical drawings.

**Which of these matches what you need?**
- (a) AI generates the full material quantities from the drawings, I just review and approve
- (b) AI gives me the specs and hardware list, I enter the quantities myself
- (c) AI gives best-effort estimates for quantities with a warning that they need verification

### 8.2 — Labor, equipment, schedule
The spec output includes `labor_estimate`, `equipment_costs`, and `construction_schedule`. These cannot be extracted from PDFs — they need to be calculated.

**Are these required for V1, or can they be added later?**
If required for V1: we need labor rate tables, crew productivity factors, and equipment rental rates as inputs.

### 8.3 — Report format
What should the PDF report look like? Specifically:
- Should it include a procurement list with quantities and prices?
- Should it include a cost summary?
- Do you have an existing estimate report format you want to match?

### 8.4 — PDF types you'll upload
The app handles two different PDF types differently:
- **Digital PDFs** (most modern plan sets) — text layer present, fast and accurate
- **Scanned/stamped PDFs** (like Paseo Miramar RTI) — image-only, slower, less accurate

**Will you be uploading both types, or mostly digital?** This affects how we prioritize the raster pipeline in V1.

### 8.5 — Hardware quantities
For Simpson hardware, the extraction gets model numbers reliably but quantities are inconsistent — sometimes we get a count from a schedule, sometimes not.

**Is a list of which models are specified sufficient, or do you need exact quantities per model for ordering?**

### 8.6 — Accuracy threshold
If the AI extracts a concrete spec as "3000 PSI at 28 days" but the drawing says "3000 psi min. (Class 1)" — is that close enough, or do you need exact verbatim text?

More broadly: what is the consequence of an extraction error? Will you always review the output before using it, or do you need the AI output to be ordering-ready without review?

---

## 9. Summary Table — Spec vs. Reality

| Spec Field | Achievable Now | With Extra Work | Not Feasible from PDFs |
|---|---|---|---|
| Project name, address, architect, SE | ✅ | | |
| Concrete PSI specs | ✅ | | |
| Lumber species + grade | ✅ | | |
| Nailing schedule | ✅ | | |
| Simpson hardware models | ✅ | | |
| Framing connection details | ✅ | | |
| Sheet list | ✅ | | |
| Special inspection requirements | ✅ | | |
| Foundation footing type + size | ✅ (specs) | | |
| Concrete cubic yards | | ⚠️ Estimated only | |
| Rebar linear feet + quantity | | ⚠️ Estimated only | |
| Lumber piece counts | | ⚠️ Low confidence | |
| Sheathing sheet count | | ⚠️ Low confidence | |
| Hardware exact quantities | | ⚠️ Partial (from schedules) | |
| Labor estimate | | ⚠️ Formula-based once quantities known | |
| Equipment costs | | | ❌ Site-specific |
| Construction schedule | | ⚠️ Phase sequence only | |
| Procurement list with prices | | ⚠️ Needs quantities + price source | |
