# 01 — Requirement Analysis

**Session:** 2026-06-20 · Analysis-only · Cross-referenced against the 6 client PDFs + committed JSON outputs.

---

## 1. Business context

Melvin Guzman runs **Mel's Builders Pro Systems** ("On Time, On Budget, Beyond Expectations"), a California residential GC focused on **foundation and rough framing**. He wants an AI tool that ingests a structural plan-set PDF and returns a **procurement-ready material takeoff + cost estimate** he can hand to a lumber yard (e.g. Ganahl) and clients.

**Business objective:** compress the manual takeoff/estimating effort — reading plans, listing materials and hardware, counting quantities, pricing labor/equipment — into an automated first draft Melvin reviews and adjusts. The explicit success bar (from `docs/PLAN.md`): *"70–80% of lines match his final order"*, as a time-saving starting point, **not** a replacement for his judgment.

**The gold standard** (memory `procurement_format.md`): a real Ganahl Lumber order **#618017, $125,665.15**, for the LHERT-SONG job — organized **by construction phase** (Material → 1st Floor → 2nd Floor → Ceiling), each line `Qty | Size | Length | Grade | Board-Footage | Price | Amount`. This is the concrete shape the output must eventually take.

---

## 2. The ten requirements (verbatim from `memory/melvin_requirements.md`)

> Analyze the uploaded plans and provide: (1) Complete material takeoff, (2) Labor estimate, (3) Equipment costs, (4) Waste factors, (5) Simpson hardware list, (6) Foundation quantities, (7) Framing lumber quantities, (8) Sheathing quantities, (9) Procurement-ready material list, (10) Suggested construction schedule. Organized by: Foundation, Floor framing, Wall framing, Roof framing. Include: Lumber sizes, Linear feet, Piece counts, Sheet counts, Concrete yardage, Rebar quantities, Hardware quantities. Output: professional estimating format ready for client proposals and procurement.

These split cleanly into **two natures** that determine feasibility:

- **Spec/identity data** (what grade, which connector, what PSI) — lives in the **text/notes/schedule layer** → reliably extractable.
- **Quantity data** (how many, how long, how much volume) — lives in **drawing geometry** (dimension lines, member grids) → **not** reliably extractable from a PDF.

This single distinction explains the entire built-vs-unbuilt gap (§5).

---

## 3. The central technical reality — the data-availability model

Validated against every sample PDF, including the gold-standard LHERT SONG:

| If the value is… | …it is | Extractable? | Examples |
|---|---|---|---|
| Written as text / in a notes block | in the PDF text layer (digital) or rasterized text (scanned) | **Yes** (text path; OCR for scanned) | Concrete PSI, lumber species/grade, nailing spec, special inspections |
| Listed in a **type-definition schedule table** | text/table | **Yes** | Footing *types* & sizes, hold-down *types*, shear-wall *types*, rebar grade/spacing |
| A **quantity/count** of distributed members | only as drawing geometry (a "TYP." callout repeated across a grid; an undimensioned wall run) | **No — physical limit** | LUS210 = 410 pcs, A35 = 500 pcs, stud counts, joist counts, wall LF, footing perimeter LF, concrete CY |
| Not in the document at all | — | **No — must be computed** | Labor, equipment, schedule, waste, prices |

**Ground-truth proof (LHERT SONG, the gold-standard project):** On the foundation plan (S-2.1) and floor-framing plan (S-2.2), hold-downs appear as **numbered bubble symbols** keyed to a HOLDDOWN SCHEDULE that defines *types* (1=HDU4, 2=HDU8…) but has **no quantity column**. To get "HDU4 = 27" you must count every "1" bubble across the grid. LUS210/A35 appear only as typed "TYP." notes and spacing rules — never as counts. **No schedule table in the set carries a quantity.** This directly tempers the `docs/PLAN.md` Priority-1 premise that "schedule tables give exact hardware quantities" — true only where a firm happens to publish a quantity column, which the gold standard does not.

---

## 4. Per-PDF requirement review (the 6 sample inputs)

The PDFs *are* the requirement: the system must handle the real variety Melvin will upload. Five different SE firms, digital vs scanned, DD vs CD vs permit-only, wood vs steel. Findings below combine direct PDF review with each file's committed JSON.

### 4.1 SVR 80% CD Set — `2026-03-31_SVR_80% CD Set.pdf` (167 pp, ~172 MB, digital/CAD)
- **Project:** San Vicente Residence, 12957 San Vicente Blvd, LA. SE: Michael Zahn Structural Engineering. Multi-discipline (T/C/A/I/M/E/P/L/S/PV), 5 consultant firms.
- **What's present:** Full text-layer specs (concrete 2500 PSI, DF grades, glulam combos, nailing); **populated framing plans exist** — S1.0 Ground, S1.1 First Floor, S1.2 Ceiling, **S1.3 Roof Framing** (J-1…J-7 joist schedule incl. TJI 560/230, glulam beams), S1.4 ADU.
- **JSON cross-check (2026-05-25 — STALE):**
  - ✅ Specs extracted well.
  - ❌ **`architect: "RODNEY MESRIANI"` is wrong** — Mesriani is the **OWNER**; the real architect is the "residential + interiors + landscape" firm at 932 Wilson St. The pipeline conflated owner-field with architect-field (the two title-block layouts differ).
  - ❌ **`total_sqft: 33030`** matches no building area (building ≈ 13,717 SF; *allowable* RFA ≈ 32,978 SF — it grabbed the zoning-basis number).
  - ❌ **`roof_framing` empty and `floor_framing` nearly empty** despite the populated S1.3 schedule — the framing plans were routed to Vision but their content didn't make it into the output. Real takeoff data left on the table.
  - ❌ **Zero `estimated` flags** despite emitting joist/beam/hardware quantities → Rule 5 violation (note: predates the June estimated-flag work; verify on re-run).
- **Doc discrepancy flagged:** `TODO.md` repeatedly states SVR "has NO S1 foundation/framing sheets (80% set)." The provided file **does** contain S1.0–S1.4 framing plans. Either the file changed since early testing or the early claim was wrong. **Impact: the pipeline may be skipping real structural data on the assumption it isn't there.**
- **Classifier edge cases:** typical-detail sheets (S2.xx, all "PER PLAN", no quantities) vs real plans (S1.x) are treated alike — detail-sheet model names get harvested as if they were plan data.

### 4.2 Whaleon Residence CD — `2026-03-03 Whaleon Residence - CD Issue Set.pdf` (73 pp, ~79 MB, digital/CAD, sparse text)
- **Project:** Whaleon Residence, 364 E. Pentagon St, Altadena. Architect: Anand Devarajan. SE: Aram Arakelyan (C82796). **Complete CD set** (foundation + framing plans present).
- **What's present:** S-2.0 foundation plan has a **PAD FOOTING SCHEDULE** (P1 18×18, P2 24×24, P3 30×30, P4 54×54, with rebar), **ANCHOR BOLT SCHEDULE** (5/8"Ø @ 48/32/24/16/12" by SW type), **HOLD-DOWN SCHEDULE** (HDU2–HDU14), **Basement Wall Schedule** (CMU), and S-2.1 has a **SHEAR WALL SCHEDULE**.
- **Text-vs-graphic confirmed:** S-2.0 text layer = **656 chars (title block only)**; footing dimensions are graphical → Vision routing is correct.
- **JSON cross-check (2026-06-17):**
  - ✅ Project info correct; footing types/sizes/rebar extracted via Gemini.
  - ❌ All footing **`linear_feet: 0`**, anchor-bolt **`qty: 0`**.
  - ❌ **Basement Wall Schedule and Shear Wall Schedule entirely missing** from output.
  - ❌ Falls back to the **2000 sqft default** for quantities **despite being a complete set** — wall LF / plywood are pure defaults, `estimated: true`.
- **Confirms:** A-series sheet numbers are **not** reliably in the text layer (the `A#-#` tokens that *are* text are detail cross-reference bubbles, not the page's own sheet number).

### 4.3 BARAGHOUSH DD Progress — `2026_05-14 BARAGHOUSH DD progress.pdf` (17 pp, ~7 MB, digital)
- **Project:** architectural-only **Design Development** set; **no S-series sheets**; every page stamped **"NOT FOR CONSTRUCTION"**; sheets explicitly defer structure ("SEE STRUCTURAL DRAWINGS").
- **JSON cross-check (2026-05-25):** ~empty result is **correct** — there is genuinely nothing structural to extract.
- **Requirement insight (UX gap):** an empty result returned in ~2 s is indistinguishable to Melvin from a crash. The document itself carries unambiguous signals the system *could* surface ("NOT FOR CONSTRUCTION" on every page; no S-sheets; explicit deferral). It should **explain** the empty result rather than return silence.
- **Bonus:** clean door (39) / window (25) schedules are present and ignored — a broader estimator could return them so a DD upload still feels useful.

### 4.4 Paseo Miramar RTI Stamped — `571 Paseo Miramar RTI Stamped Plans.pdf` (57 pp, ~216 MB, fully scanned/raster)
- **Project:** Hunt Residence (fire rebuild), 571 Paseo Miramar, Pacific Palisades. SE: KOBE. **Zero text layer** — confirmed (57 chars total = form-feeds; no embedded fonts). This is the file that justifies the OCR/Vision path.
- **What's present & legible:** at full render the SHEAR WALL / GRADE BEAM / BEAM / FRAMING schedules are crisp and OCR-able (Fc=3000 PSI, #5/#7 rebar, 16d @ 4", PLF values). Footing dimensions on the *plan* are geometry-only.
- **JSON cross-check (2026-06-18 — NEWEST artifact):**
  - ❌ **`project` block entirely empty** (name/address/architect/SE/sqft all blank) despite the cover plainly showing HUNT RESIDENCE / 571 Paseo Miramar / RNA.
  - ❌ **`concrete_specs`, `nailing_schedule`, `lumber_specs` all empty** — because **all 13 schedule pages failed PaddleOCR** with `ConvertPirAttribute2RuntimeAttribute` (the Python-3.13 runtime break). 4 additional Vision `parse_error`s.
  - ❌ Hardware polluted with generic/placeholder entries ("Bolts", "Weld", "A325", "2x6" as a model) and **lingering noise codes AB123 ×7, LS456 ×4, PSS1 ×6**.
  - ⚠️ This artifact **contradicts** `melvin-testing-guide.md`, which tells Melvin to expect "128.6 ft LF, 10.7 CY, 8 footing types, 40+ hardware" for this file. That success was a Docker run, not captured here.
- **Classifier edge cases:** civil (C-5 Erosion Control), Title-24 energy forms (T24-2), and architectural notes were all bucketed as "schedules" and sent to the broken OCR path.
- **Operational risk:** **216 MB upload** will exceed default FastAPI/Starlette and typical gateway limits (often 100 MB); 57 raster pages are memory-heavy and slow.

### 4.5 Woodlane Court — `4248 Woodlane Court - All Plans.pdf` (60 pp, ~144 MB)
- **Project:** WLV 1 Development Residence, 4248 Woodlane Court, Westlake Village. SE: JT Engineering. **Architectural permit set; no wood S-series framing sheets.** Page 1 is a *civil* grading cover (different consultant, W.E.M.). Pages 37–39 are the **LA City "Standard Quality Assurance Plan for Steel Moment Frames"** — i.e. **this is a steel-moment-frame house.**
- **JSON cross-check (2026-06-09):**
  - ✅ Empty lumber/concrete/nailing/foundation is the **correct** outcome (no wood structural sheets).
  - ❌ The "framing connections" it produced (FCAW TC-U4a-GF, SMAW TC-U4a, Backing Bar, Doubler Plate) are **steel weld-process codes from a generic city standard plan — noise, not procurable hardware.**
  - ❌ Vision pages (23/26/33/34/36/46) produced **fabricated** wood hardware (HT-10 ×20, LB-5 ×15, MB-123 ×4, A325 ×24) with round made-up quantities and boilerplate notes — hallucination, unflagged. Rule 5 violation.
  - ❌ **9 pages lost to Gemini 429 rate-limits** → coverage incomplete; "empty framing" is not fully proven.
- **Requirement insight (scope mismatch):** a steel-MF residence is **outside Melvin's stated "foundation and rough framing" (light wood) scope.** The wood-oriented pipeline has nothing real to extract here and instead pads the output with invented hardware. The system should *detect structural type* and decline / flag, not fabricate.

### 4.6 LHERT SONG CD Bid Set — `2025_09-30 LHERT SONG CD Bid Set.pdf` (64 pp, ~35 MB, digital/CAD) — **the gold-standard project**
- **Project:** Lhert-Song, 3333 Cabrillo Blvd, LA. Architect: Letter Four. SE: Ashley & Vance (Sean Galbreath S5653). We hold the **real Ganahl order** for this job.
- **Structure:** only three structural plan sheets — **S-2.1 Foundation & Basement, S-2.2 2nd-Floor Framing, S-2.3 Roof Framing.** There is **no standalone 1st-floor framing plan** (1F framing is the underside on S-2.2). Schedules on plan pages are all **type-definition** tables (Shearwall/Strongwall/Holddown/Strap) with **no quantity column**.
- **CORE CLAIM — confirmed by the gold standard itself:** the real order's LUS210 = 410, A35 = 500, HDU4 = 27, plus hundreds of TJI joists and plywood sheets, are **not present anywhere as readable totals.** They are distributed "TYP." callouts / bubble symbols requiring grid-counting. **Full quantity takeoff is not achievable from this document by text/OCR.**
- **JSON cross-check (2026-06-15):**
  - ✅ Project info correct (name/address/architect/SE).
  - ❌ **`total_lf: 0`, `concrete_cubic_yards: 0`, `concrete_specs` empty** — directly contradicts memory's "LHERT SONG 76.8 ft confirmed." (This artifact predates the June-18 LF-scope fix; the "76.8 ft" lives only in an uncaptured server run.)
  - ❌ **`roof_framing.hardware` polluted with electrical items** (LUTRON, LEVITON, HUBBEL) — bleed-through from lighting pages.
  - ❌ Concrete spec (2500 psi, slump 5", slab #4@16") **missed**; anchor bolts returned generic **1/2"** when the shear-wall schedule specifies **5/8"**.

---

## 5. Requirement → capability mapping (corrected against ground truth)

| # | Requirement | Honest state | Evidence / limit |
|---|---|---|---|
| 5 | Simpson hardware **list (models)** | ✅ Reliable | Models extracted across all CD sets |
| — | Lumber **species/grade** | ✅ Reliable | Text layer |
| — | Concrete **PSI**, rebar **grade/spacing** | ✅ Reliable (digital); ⚠️ scanned depends on OCR working | Paseo lost all concrete specs to OCR break |
| — | Nailing schedule | ✅ digital; ⚠️ scanned (OCR) | |
| — | Framing connection details | ✅ but noisy | Steel/electrical/arch noise leaks in (Woodlane, LHERT) |
| 6 | Foundation **specs** (types/sizes) | ⚠️ Partial | Types ✅; **LF/CY = 0** on CAD |
| 8 | Sheathing **sheets** | ⚠️ Estimated | Formula from sqft (87 vs real 86 once — but on default 2000 sqft when sqft missing) |
| 5 | Hardware **quantities** | ❌ Hard limit | LUS210 0–12 vs **410**; A35 4 vs **500** — geometry counting |
| 1 | **Complete material takeoff** | ❌ | Depends on LF + piece counts |
| 7 | Framing lumber **quantities** | ❌ | Member counting from plans |
| 6 | Concrete **CY**, rebar **LF/qty** | ❌/⚠️ | CY derived from LF; LF = 0 on CAD |
| 9 | **Procurement-ready list** (by phase, Ganahl format) | ❌ | Gated on quantities; output still type-organized, not floor-organized |
| 2 | Labor estimate | ✅ Built | rate sheet × quantities |
| 3 | Equipment costs | ✅ Built | derived (pump/crane/scaffold) |
| 4 | Waste factors | ✅ Built | lumber/plywood +10%, concrete +8% |
| 10 | Construction schedule | ❌ | Blocked on Melvin's production rates |

**Tally:** of 10, ~3 fully delivered (hardware *list*, labor, equipment) + waste; ~3 partial (foundation specs, sheathing est., specs-on-scanned); ~4 not delivered (full takeoff, lumber quantities, procurement list, schedule). Matches the project's own "~30%" self-assessment — and the unbuilt majority is dominated by the geometry limit, not by remaining effort.

---

## 6. The strategic framing the project already identified (and where it stands)

`docs/findings-and-feasibility.md` posed the right fork:
- **Path A** — deliver specs + hardware list reliably; **Melvin enters quantities himself.** Buildable, accurate.
- **Path B** — AI generates full quantity takeoff from drawings. 4–6 weeks R&D, accuracy not guaranteed.
- **Path C (hybrid)** — best-effort estimates flagged `estimated: true`.

**What actually happened:** the project drifted into **Path C** (quantities.py estimates + waste + cost) **without an explicit client decision on the fork** — the six client questions in findings-and-feasibility §8 were never answered (client unresponsive). This is a requirement-process gap: a scope-defining decision was made implicitly. See `03` D-1 and `04` Q-1.
