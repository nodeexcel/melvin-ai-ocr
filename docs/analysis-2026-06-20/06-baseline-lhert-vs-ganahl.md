# 06 — Captured Baseline: LHERT SONG (current code) vs Ganahl EST618017

**Run:** 2026-06-20, `venv/melvin311` (Py 3.11) direct interpreter via `app/backend/scripts/test_pdf.py`. **Exit 0, 37.8 min, 0 parse errors.** This is the first *captured, reproducible* baseline (partially addresses the no-baseline finding for LHERT; other 5 PDFs still uncaptured). Output: `scratchpad/baseline_lhert_2026-06-20.json`.

> Caveat: this is the **CLI path**, which has the OCR-scope drift (LF over-scoped). The web-app path (`pipeline_worker`) would differ on footing LF only.

## Run summary
Project LHERT-SONG · SE Ashley & Vance ✅ · 13 sheets ✅ · 30/64 relevant · methods: 18 text / 9 gemini / 3 gpt-vision · 0 errors. Hardware 41 · framing 104 · **nailing 0** · lumber 5 ✅ · concrete 7 ✅. Footing LF **903.8** · CY **83.7** (both wrong, see below). 13 `estimated:true` flags present (Rule 5 honored for quantities).

## Verified current-code defects (fresh run, NOT stale artifacts)

| # | Defect | Evidence | Root cause | Severity |
|---|---|---|---|---|
| B-A | **Wrong address** "8004 GONZAGA AVE…90045" (correct: 3333 Cabrillo Blvd) | bad addr on pages 3,4,5,6,8 (5); correct "CABRILLO" on 7,55,56,57 (4) | `aggregate._most_common` picks the value on *more* pages; the wrong addr (architect/reference) out-votes the title-block addr | High (client-facing) |
| B-LF | **Footing LF 903.8 ft / CY 83.7** (correct ≈ 76.8 ft) | log + JSON | CLI OCR scope = {foundation,floor,roof}; framing-plan span dims summed as footing LF (the drift, `05` Q2) | High (orderable number) |
| B-SQFT | **total_sqft=0 → 2000 default** → quantity estimates ~10× low | quantities.total_sqft=2000; Ganahl board-ft=43,452 | sqft not extracted from this set; 2000 fallback far too small for this large building | High (quantities meaningless) |
| B-NOISE | **~8 non-structural items in `simpson_hardware`** raw_json: SLRA-125, NEOFLEX, "Bronze Pemko #108 B", "Schluter Jolly", C-Channel, HSS2x2x3/16, SDS, "Simpson LUS/LTS Hangers" (generic) | hardware list | noise filter runs only in `generator.py` (render), not in stored data (`02` F-8) | Med |
| B-NAIL | **nailing_schedule = 0** | JSON | LHERT nailing lives in detail diagrams on S-1.1, not a text table; not captured by any path | Med |
| B-ANCH | **anchor_bolts size "1/2\" DIA."** (shear-wall schedule specifies 5/8") | foundation.anchor_bolts | Gemini grabbed a generic value, missed the schedule | Med |
| B-HWCOUNT | Hardware counts far under: A35×9, HDU4×3, LTP4×10, CMSTC16×10 | hold_downs/hardware qty_source=ocr_callout | counting ceiling (`05` Q1) — callouts ≠ installs | Expected (hard limit) |

## What works well (don't disturb)
- Project name, SE, sheet list (13) ✅ · concrete specs incl. rebar dev tables (7) ✅ · lumber design values GLB/LVL/LSL/PSL (5) ✅ · framing connections (104) ✅ · Rule-5 estimated flags ✅ · TJI model captured ("11-7/8 TJI 210") ✅.
- **Current code > committed June-15 JSON** (which had concrete empty, LF 0) — proves the on-disk artifacts understate current quality (the stale-baseline finding cuts both ways).

## Gap vs EST618017 (the target)
The Ganahl order = 265 lines, $125,665, **43,452 board-ft, 16,144 sq-ft**, organized Material/1st/2nd/Ceiling. The baseline produces: correct **specs & models**, wrong/placeholder **quantities**, no **lengths**, no **board-footage**, type-organized (not phase-organized).
- **Reachable now (extraction):** the spec/model columns, footing types, hardware model list (de-noised), schedule data (with table-structure OCR).
- **Not reachable without detection/DXF/service (counting):** every QTY and LENGTH column — i.e. the procurement substance. Confirmed by AECV-Bench (`05` R1) and by B-HWCOUNT here.

## Immediate fixes this baseline justifies (for a future implementation session — not done here)
1. **Address aggregation** — don't use raw most-common; prefer the title-block address (appears on structural sheets / co-located with project name / highest-confidence page). B-A.
2. **Unify OCR scope** (foundation-only) across CLI + web app. B-LF. *(validation experiment running)*
3. **sqft fallback** — when sqft unknown, do not silently use 2000; either extract from an area sheet, mark quantities low-confidence, or scale from footprint. B-SQFT.
4. **Move noise filter to the data layer** (allowlist) so raw_json is clean. B-NOISE.
5. **Recover nailing** from detail diagrams (tiling/table-structure or a dedicated nailing-from-details prompt). B-NAIL.

## Experiments still queued against this baseline
LF-scope validation (running) · tiled/table-structure recovery of nailing (B-NAIL) · cross-model on a dense schedule page · JSON-mode on scanned pages (Paseo) · PaddleOCR `enable_mkldnn=False` on Py-3.13.
