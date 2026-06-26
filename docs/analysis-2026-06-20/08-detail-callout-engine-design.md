# 08 — Detail-Callout Extraction Engine — Design (spike-validated)

**Date:** 2026-06-25 · **Status:** feasibility proven end-to-end on two real plans; design ready; build is a multi-week effort (gated on API spend-limit being raised for validation runs).

This is the core feature behind Melvin's quantity ask (`07`). It computes hardware quantities the way a human estimator does: count detail callouts → open each referenced detail → read its hardware → multiply.

---

## 1. Why this approach
Counting distributed *unlabeled* members (LUS210 ×410) is intractable for vision models (AECV-Bench 0.40–0.55, `05` R1). But callouts are **discrete labeled markers** — far more tractable, and it's how estimators actually work (`07` §4).

## 2. Feasibility evidence (two spikes, 2026-06-25)
| Plan | Modality | Callouts | Detail sheets | Chain verdict |
|---|---|---|---|---|
| 8603 Rugby (Terra Nova) | **vector CAD** | circle `detail#/SDx`, **in text layer** (SD1×26, SD2×26, SD3×31) | absent (partial draft) | count+resolve feasible; detail-read untested (no detail sheets) |
| 3611 Locke | **raster JPEG in PDF, hand-lettered** | circle `detail#/S4`, **graphical-only (needs vision/OCR)** | **present (S4)** | **full chain WORKS**: `1/S4`→ST22/PC/PBS/LUS; `2/S4`→A307 bolts/SDS/A35 |

**Conclusion:** detect → resolve → read-hardware is real. The engine must be **multi-modal** (text-layer for CAD, vision/OCR for raster/handwritten).

## 3. Architecture — staged pipeline (reuses existing modules)
```
plan PDF
  │
  1. CLASSIFY pages            (reuse classify.py) → {plan pages, detail-sheet pages, schedules}
  │
  2. DETECT + COUNT CALLOUTS   per plan page
  │     • CAD/text path:   regex `(\d+[A-Z]?)\s*/\s*(<sheet-id>)` from text layer
  │     • raster path:     render ≥400dpi → detect circle markers (vision) → OCR the #/sheet
  │     • classify marker SHAPE: circle=detail-ref | diamond/triangle=enlarged/length | plain=gridline
  │     → counts[(detail#, sheet#)] = N   (key on the PAIR; numbers restart per sheet)
  │
  3. RESOLVE callout → detail  locate detail-sheet page by sheet#, locate the detail cell by its "#/sheet" stamp
  │
  4. EXTRACT detail hardware   text (CAD details) OR vision/OCR on high-dpi crop (raster/handwritten)
  │     → parse Simpson models + fasteners
  │     → VALIDATE each model vs Simpson catalog/allowlist (reuse hardware.is_real_model + a positive catalog)
  │
  5. ROLL UP                   per detail: hardware × callout-count; aggregate by phase
        → quantities with provenance: source="callout(detail N/sheet × count)", estimated=true until validated
```
**Module reuse:** `classify.py` (stage 1), `ocr.py`/PaddleOCR (raster detect+OCR), `extract.py` Gemini/GPT vision (raster crops), `hardware.py` (model normalisation + validity + a new positive Simpson allowlist), `aggregate.py` (rollup + provenance).

## 4. Key design rules (from the spikes)
- **Always key on the full `detail#+sheet#` pair** — detail numbers restart per sheet; a bare number is ambiguous.
- **Marker-shape classification is required** — don't conflate detail-ref circles with diamond/triangle (shearwall/length) markers or plain gridline bubbles.
- **Two modalities, auto-detected per page:** text-layer present + vector → regex path; raster/image body → vision+OCR path. (A page can be CAD title-block + raster drawing — detect at the drawing-body level.)
- **Validate model strings, never trust hand-lettered OCR blind** (Rule 5) — match against a Simpson catalog/allowlist; flag low-confidence.
- **callout-count ≈ install-count, not exact** — a "TYP." callout may imply more than its marker count; keep results `estimated` and let Melvin adjust (he applies an experience buffer anyway, per `procurement-format`).

## 5. Validation plan
- Score engine output against Melvin's **supplier EST lists** (he sent ~8). **Requires plan↔order pairs** — ask Melvin which EST corresponds to which plan (the EST numbers don't map to plan addresses; only the known LHERT pair exists today).
- Per-firm test set: at least one CAD (text-layer) plan + one raster/hand-lettered plan + one scanned plan.
- Gate each stage on a captured baseline (the `no-reproducible-baseline` discipline).

## 6. Risks / open items
- **Handwriting OCR accuracy** on Simpson model numbers (3611 Locke details are hand-lettered) — mitigate with ≥400dpi per-detail crops + catalog validation.
- **Per-firm callout-format variance** — circle vs diamond vs hexagon, sheet-id naming (SD1 vs S4 vs D-1). Detection must be firm-agnostic (shape + proximity), not a per-firm regex (the `feedback_no_patches` lesson).
- **API cost** — vision on many high-dpi crops per plan adds cost; bound by only processing detected callout/detail regions, not whole sheets. (Org spend limit currently paused — raise before validation runs.)
- **Compute** — high-dpi crops are lighter than full-sheet PP-Structure (which crashed the dev box); crop-then-process avoids that.

## 7. Phasing
1. ✅ Spike (done — chain proven both modalities).
2. Build **stage 2 detection** (text path first — cheap, deterministic on CAD), then raster/vision path.
3. Build **stages 3–4 resolution + detail-hardware extraction** (vision/OCR + catalog validation).
4. **Stage 5 rollup** with provenance + estimated flags into the existing report.
5. **Score vs EST lists**, iterate per firm.

Build is multi-week; each stage is independently testable against a captured plan. This is the honest basis for the "accurate quantities" timeline given to Melvin.
