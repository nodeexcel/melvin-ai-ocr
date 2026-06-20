# 05 — Extraction Method Improvements & Experiment Plan

**Session:** 2026-06-20 · Derived from direct reading of `classify.py`, `extract.py`, `ocr.py`, `prompts.py`, `runner.py`, `test_pdf.py`. Each lever cites file:line, states the hypothesis, the expected gain, and a concrete experiment to validate it. Web-research-sourced methods (table-structure OCR, vision-model benchmarks, counting) are tracked separately and merged when the two background research agents report.

**Two accuracy problems, kept separate:**
- **(E) Extraction** — read what's *on* the page (specs, schedules, hardware models, footing data). Many fixable levers below.
- **(Q) Quantity takeoff** — the counts/lengths that fill the Ganahl order columns. Largely a hard geometry limit; only DXF / vision-counting / specialist routes can move it (see `03` C-R10; research pending).

---

## E-levers (extraction accuracy) — ranked by expected value / effort

### E1 — Use native JSON mode (HIGH value, LOW effort) ✅ code-confirmed gap
- **Evidence:** `extract.py:32` (GPT-4o text), `:126` (GPT-4o vision), `:55/:86` (Gemini) call the models with a free-text "return JSON only" instruction in `SYSTEM_PROMPT` but **do not set** OpenAI `response_format={"type":"json_object"}` or Gemini `response_mime_type="application/json"`. `_parse_response` (`:19-26`) then does a brittle ```-fence strip and `json.loads`; any prose around the JSON → `parse_error`.
- **Hypothesis:** Native JSON mode eliminates most `parse_error`s and refusals-as-text, recovering pages currently lost.
- **Expected gain:** Directly reduces the documented ~5–8% parse-error rate and the "valid-JSON-but-wrapped" failures.
- **Experiment:** Re-run the specific pages that produced `parse_error`/empty in the committed JSONs (e.g. LHERT p60 roof, Whaleon refusals) with JSON mode on; measure recovered fields. Cheap (few pages).
- **Risk:** JSON mode caps some models' creativity but we want strict JSON — net positive. Keep `_parse_response` as a fallback.

### E2 — Tile / crop dense pages for vision (HIGH value, MED effort) ✅ code-confirmed gap
- **Evidence:** `runner.py:18` renders vision pages at **dpi=250**; `extract.py:15` re-encodes **JPEG quality=85**; `extract.py:134` sends a **single image** with `detail:"high"`. A 34×44" E-size sheet at 250 DPI ≈ 8500×11000 px; GPT-4o high-detail tiling caps effective resolution, so 9-pt schedule rows render to a handful of pixels and are lost (this is exactly the Paseo "Vision misses dense tables at 250 DPI" root cause in `pipeline-findings.md §13`).
- **Hypothesis:** Splitting a dense page into overlapping tiles (the pipeline already has `_render_tiles` in `ocr.py:74` for OCR) and extracting per-tile, then merging, captures small text the single-image path drops.
- **Expected gain:** The single biggest lever for schedule/callout completeness on both digital and scanned plans.
- **Experiment:** On one known-dense page (LHERT S-1.2 lumber specs; a hold-down schedule), compare (a) current single-image vision vs (b) 4-tile vision merge vs (c) higher DPI single image. Score against the visible ground truth.
- **Cost note:** tiling multiplies vision calls per page — weigh against accuracy. Crop-to-schedule-region (detect table bbox first) is the cost-efficient variant.

### E3 — Table-structure recognition for schedules (HIGH value, MED effort) ✅ code-confirmed gap; method TBD by research
- **Evidence:** `ocr.py:284-328` `extract_text_from_scanned_page` runs plain `ocr.predict()` and **flattens** detected text into reading-order lines (`cy//20` buckets). Table **cell/column association is destroyed** — a nailing or grade-beam schedule becomes a soup of tokens, so the downstream LLM must guess which value belongs to which row.
- **Hypothesis:** Converting the table *image* to structured rows/cells (PaddleOCR **PP-StructureV3** table recognition, or a cloud doc-AI table parser — research agent comparing) before the LLM step yields far more complete, correctly-associated schedule rows.
- **Expected gain:** Recovers the nailing/lumber/concrete/hold-down schedules that come back partial or empty — the bulk of reliably-extractable value.
- **Experiment:** Run PP-Structure (and one cloud table parser if cheap) on a scanned schedule page (Paseo nailing schedule) and a digital one rendered to image; compare extracted rows vs the page.
- **Dependency:** needs the PaddleOCR Py-3.13 crash resolved or Docker (research agent investigating `ConvertPirAttribute2RuntimeAttribute`).

### E4 — Raise/chunk output token budget on dense pages (MED value, LOW effort)
- **Evidence:** `extract.py:38` and `:138` set GPT-4o `max_tokens=8000`; dense soils/notes pages are documented to truncate (`findings-and-feasibility §7`). Gemini is at 16000 (`:81`).
- **Hypothesis:** Raise GPT-4o cap (model supports more) or chunk very long text inputs; eliminates silent truncation.
- **Experiment:** Re-run a known-truncating page (Paseo soils notes) at higher cap; check completeness.

### E5 — Robust JSON salvage fallback (LOW value once E1 lands, LOW effort)
- **Evidence:** `_parse_response` (`extract.py:19-26`) only handles a leading ```-fence. If the model emits leading prose, parse fails.
- **Hypothesis:** Regex-extract the outermost `{...}` as a fallback before declaring `parse_error`. Belt-and-suspenders with E1.

### E6 — Surface OCR-unavailable vs OCR-empty (MED value, LOW effort) ✅ code-confirmed
- **Evidence:** `ocr.py` returns `{}`/`""` on *every* failure mode — PaddleOCR not installed, runtime crash (the Py-3.13 `ConvertPirAttribute` break), or genuinely no text — indistinguishably. `runner.py:218` swallows OCR errors into a progress message. So a broken OCR run looks identical to "no data on the page" (this is why the Paseo committed JSON is silently empty).
- **Hypothesis:** Distinguish and record the cause in the result (`ocr_status: unavailable|error|empty|ok`); fail loud in dev.
- **Expected gain:** Prevents shipping silently-empty results as if they were clean (trust + the no-baseline problem).

---

## Q-levers (quantity takeoff) — the hard problem

### Q1 — Hardware counting cannot reach TYP counts, and misses models ✅ code-confirmed ceiling
- **Evidence:** `ocr.py:135-154` `_STRAP_PATTERNS` is a hardcoded list of ~18 connectors that **does not include `LUS*`** (the 410-count item) and counts **each OCR occurrence as 1 install** with 80-px dedup (`:155`). A single "LUS210 TYP." note that applies to 410 joists is counted as 1. This is why output shows LUS210 ≈ 0–12 vs real 410.
- **Conclusion:** Counting callouts ≠ counting installs. This is the geometry ceiling (`02` F-9), not a tunable bug. No counting-pattern change fixes it.
- **Only real routes (research pending, do not build speculatively):** (a) **DXF/CAD layer files** + `ezdxf` member count; (b) **vision object-detection / grid-counting** on framing plans; (c) **specialist takeoff service** (iBeam/Togal/Kreo). All are scope/procurement decisions.

### Q2 — Footing LF heuristic is fragile and scope-drifted ✅ code-confirmed
- **Evidence:** `ocr.py:29-37` `DIM_PATTERN` + `EXCLUDE_KEYWORDS` sum dimension strings not near excluded words → noisy. **Scope drift:** `test_pdf.py:25,114-117` runs LF on `{foundation,floor_framing,roof_framing}` (old broad scope → inflated LF, e.g. LHERT 903.8 ft) while `runner.py:194-197` (web app) runs LF on `foundation` only (→ 76.8 ft). The two run paths disagree.
- **Fix (real, not patch):** Move OCR orchestration *inside* `run_pipeline_sync` (or a shared helper) so CLI and web app share one scope. Eliminates the drift the "single codebase" principle is supposed to prevent.

### Q3 — Estimates emitted without provenance (Rule 5) ✅ code-confirmed risk
- **Evidence:** `prompts.py` foundation/floor/roof prompts request `qty_pieces`, `linear_feet`, `concrete_cubic_yards` — values the model cannot read from geometry, so it returns 0 or hallucinates (Woodlane fabricated hardware). `estimated:true` is applied inconsistently (0 occurrences in SVR JSON).
- **Fix:** Tag every numeric with `source: read|schedule|ocr|estimated`; never surface a non-`read` number without the flag; drop hardware that doesn't match a Simpson allowlist (also fixes the denylist anti-pattern, `02` F-8).

---

## Prioritized experiment queue (validate before any implementation)

| # | Experiment | Proves | Cost |
|---|---|---|---|
| X1 | Phase-0 baseline: LHERT via 3.11 interpreter, diff vs EST618017 | current true state; quantifies the gap | 1 run (running now) |
| X2 | JSON mode on previously-failed pages | E1 gain | low |
| X3 | Tiled vs single-image vision on 1 dense schedule page | E2 gain | low |
| X4 | PP-Structure (or cloud) table parse on 1 scanned + 1 digital schedule | E3 gain | low |
| X5 | Cross-model (GPT-4o vs Gemini-2.5 vs Claude) on same dense page | best model per task | low |
| X6 | Unify OCR scope; re-confirm LHERT LF = 76.8 via CLI | Q2 fix | 1 run |
| X7 | PaddleOCR Py-3.13 fix (PIR flag/pin) or confirm Docker-only | E3/E6 unblock | low |

**Discipline:** every experiment scored against a *visible ground truth* (the PDF page) or against EST618017 for quantities. No method adopted on vibes. Results appended here as they land.

---

## Web research findings (2026-06-20, two background agents, sourced)

### R1 — The counting ceiling is empirically confirmed (decisive for scope)
- **AECV-Bench** (arXiv 2601.04819, 2026) tested frontier multimodal models (Claude Opus 4.5, Gemini 3 Pro, GPT-5.2, Qwen3-VL) on AEC drawings: **text/OCR extraction ≤ 0.95**, but **symbol counting only 0.40–0.55 — "remains unsolved."** "VLMs Can't Even Count to 20" (arXiv 2510.04401) shows counting accuracy collapses past ~5–7 instances.
- **Implication:** No VLM (GPT/Gemini/Claude) will reliably count LUS210 (~410) / A35 (~500). Q1 is a documented hard limit, not a prompting gap. **Counting must move off the VLM to a dedicated detector.**
- **Real counting routes (ranked):** (1) **fine-tuned YOLOv8/v11 + SAHI tiled inference** — the proven industry method (Roboflow deployed per-sheet-type symbol detectors; SAHI adds +6–14% AP on small objects); needs labeled symbols (5–10 plan sets/sheet type). (2) **GroundingDINO/Grounded-SAM or CountGD exemplar counting** — "here's one LUS210, find them all" — lower label budget, good bootstrap. (3) **Outsource** (Togal.AI ~98% on geometry but human-in-loop; Beam.AI) — also use to obtain a ground-truth count to validate against.

### R2 — Extraction IS improvable now; best methods
- **Best VLM for extraction (value):** **Gemini 2.5 Pro** — top OCR + best localization among LLMs (RF100-VL mAP 13.3 vs GPT-5 1.5), `media_resolution` knob for fine text, ~$1.25/$10 per M tok. The pipeline currently uses **gemini-2.5-flash** (cheaper, weaker) and **GPT-4o** (now dated) → **model upgrade is a lever.** **Claude Opus 4.x** = strongest structured/JSON reasoning over messy schedules but priciest ($5/$25) — reserve for hard pages.
- **High-res strategy (confirms E2):** render ≥200 DPI, **tile with overlap**, ROI-crop the schedule/grid away from title block, merge+dedup at tile boundaries. Provider tiling downsamples full E-size sheets (Gemini 768px tiles; OpenAI 512px tiles after ≤2048 longest-side), which is exactly why current single-image extraction drops small rows.

### R3 — Table-structure recognition for schedules (fixes E3)
- Flat OCR loses the grid; need a **table-structure** stage emitting cells with row/col indices. Options:
  - **AWS Textract `AnalyzeDocument` TABLES** — **$15/1,000 pages**, true cell objects + merged-cell relations, strong on dense line-items, **CPU/no-GPU, boto3 in an afternoon.** Best cheap path for a self-funded project. *(needs the AWS-credentials decision — `04` D-block.)*
  - **PaddleOCR-VL-0.9B** (Oct 2025) — table TEDS ~0.92 SOTA, **GPU-only (≥8 GB VRAM)**. Best if a GPU is available.
  - **PP-StructureV3** — CPU-capable, already in the project's Paddle ecosystem, mature. **Lowest-friction first pilot** (no new vendor).
  - **pdfplumber/Camelot** — free + accurate but **only on vector/digital PDFs** → add a cheap "is this page vector?" fast-path for digital sets (SVR, LHERT, Whaleon, Woodlane), reserve VLM/Textract spend for scanned (Paseo).

### R4 — PaddleOCR crash: real root-cause fix (resolves E6/X7)
- `ConvertPirAttribute2RuntimeAttribute` is a **PaddlePaddle 3.3.0 regression** in the PIR→oneDNN path, thrown at `predict()`. The "Py-3.13" symptom is incidental (3.13 resolver pulled the 3.3.0 build). **Fixes:** (1) hard-pin `paddlepaddle==3.2.0` via a **pip constraints file** so it can't drift (Dockerfile already pins; harden it); (2) if forced to 3.3.0, construct the predictor with **`enable_mkldnn=False`** (a.k.a. `use_onednn=False`) to bypass oneDNN. Confirmed-good pairs: 3.2.0+paddleocr 3.3.0 (current), 3.2.2+3.4.1, 3.0.0+3.4.1. Sources: Paddle #77340, PaddleOCR #17350, PaddleX #4970.
- **Worth testing:** `enable_mkldnn=False` may make OCR run on the local Py-3.13 venv too, unblocking local iteration (X7).

### Net method roadmap (research-grounded)
- **Extraction (now, in-house/cheap):** native JSON mode (E1) · ≥200 DPI + tiling/ROI (E2) · model upgrade GPT-4o→Gemini-2.5-Pro, Claude for hard pages (R2) · PP-StructureV3 table stage, pdfplumber vector fast-path (E3/R3) · pin-harden PaddleOCR + try `enable_mkldnn=False` (R4) · OCR status surfacing + Rule-5 provenance (E6/Q3).
- **Counting (project-level decision, not a quick fix):** YOLO+SAHI detector build OR exemplar-counting bootstrap OR outsource — pick per build-vs-buy appetite; until then, label every count `estimated`.
- **Decisions that gate the bigger pilots** (defaults chosen since client/owner unresponsive): GPU available? → if no, Textract for tables. AWS creds OK? Build vs outsource counting? Model-upgrade budget? See `04`.

---

## Experiment results log

**X1 — Phase-0 baseline (LHERT, CLI, current code), 2026-06-20:** done. See `06-baseline-lhert-vs-ganahl.md`. 37.8 min, 0 errors; specs/models good, quantities/counts wrong; 6 current-code defects root-caused.

**X6 — LF-scope fix, 2026-06-20:** ✅ **PROVEN.** `extract_lf_from_pages` on foundation-only (page 58, S-2.1) = **76.8 ft**; on broad scope {foundation,floor,roof} = **903.8 ft**. The 827-ft inflation is entirely framing-plan dimensions (p17 190.8, p19 234.0, p31 139.5, p59 63, p60 58, …). Confirms the CLI vs web-app drift (`06` B-LF). Fix = unify OCR orchestration to foundation-only inside a shared helper. PaddleOCR ran offline from cached PP-OCRv5 models. Note: `memory/lf_extraction_findings` is only half-correct — fixed in web app, still broken in CLI.
