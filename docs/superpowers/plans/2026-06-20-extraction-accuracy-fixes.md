# Extraction Accuracy Fixes — Implementation Plan

> **For agentic workers:** steps use checkbox (`- [ ]`) syntax. Spec → implement → test → commit.

**Goal:** Fix two verified, root-caused extraction defects that produce wrong client-facing numbers/metadata: (1) the OCR footing-LF scope drift + dead hardware-counting pass, and (2) the project-address aggregation picking the wrong address.

**Architecture:** Eliminate the duplicated OCR orchestration in `test_pdf.py` and `pipeline_worker` by extracting one shared `run_ocr_passes()` (single source of truth, foundation-only LF scope). Separate hardware-count injection from LF injection so hardware counting works independently of footing LF. Make project name/address resolution prefer structural title-block pages (identified by co-present structural engineer) over raw frequency.

**Tech Stack:** Python 3.11, PaddleOCR 3.3.0/PaddlePaddle 3.2.0 (Docker / `venv/melvin311`), pytest. No new dependencies.

## Global Constraints (from CLAUDE.md + analysis)
- **Rule 4:** Pipeline changes must be validated against real test-PDF data before "done".
- **Rule 5:** Never return unverified quantities unflagged (`estimated: true`). Preserve existing flagging.
- **Rule 6:** Schema changes cascade to report + frontend. **This increment changes VALUES only, not `raw_json` field shapes** — no cascade.
- **No patches:** fix root causes (de-duplicate OCR orchestration), don't add workarounds.
- Only stage files I create/modify — the working tree has unrelated pre-existing WIP (`app/docker-compose.yml`, `app/frontend/package.json`, …). Never `git add -A`.
- Evidence anchors: `docs/analysis-2026-06-20/06-baseline-lhert-vs-ganahl.md` (B-LF, B-A) and `05` (Q2, experiment X6: foundation-only LF = 76.8 vs broad 903.8).

## File Structure
- `app/backend/app/pipeline/aggregate.py` — MODIFY: add `_resolve_project_field`, `inject_hardware_counts`; slim `inject_lf_data` to LF-only; switch project name/address resolution.
- `app/backend/app/pipeline/runner.py` — MODIFY: add `_ocr_page_indices` + `run_ocr_passes`; call it from `pipeline_worker`; import `inject_hardware_counts`.
- `app/backend/scripts/test_pdf.py` — MODIFY: replace inline OCR blocks + subprocess fallback with `run_ocr_passes`; fix summary to read foundation LF from `result`.
- `app/backend/tests/test_extraction_fixes.py` — CREATE: unit tests for the pure logic + a real-data re-aggregation test.

---

## Task 1: Shared OCR orchestration (foundation-only LF + live hardware pass)

**Why:** `test_pdf.py` (broad LF scope {foundation,floor,roof}) and `pipeline_worker` (foundation-only) disagree → CLI reports 903.8 ft, web app 76.8 ft (drift). Separately, `inject_lf_data` early-returns when `grand_total_lf==0`, so the dedicated Pass-2 hardware injection in BOTH callers is dead code — hardware callouts only survive from pages the LF pass happens to scan. Foundation-only LF would therefore *shrink* hardware counts unless hardware injection is decoupled. Fix both at the root with one shared function.

**Files:** Modify `aggregate.py`, `runner.py`, `scripts/test_pdf.py`; Test `tests/test_extraction_fixes.py`.

**Interfaces produced:**
- `aggregate.inject_lf_data(result: dict, lf_data: dict) -> dict` — now LF/CY/scale only.
- `aggregate.inject_hardware_counts(result: dict, ocr_counts: dict[str,int]) -> dict` — merges callout counts into `simpson_hardware` + `hardware_by_phase`; runs regardless of LF.
- `runner._ocr_page_indices(pages: list[dict]) -> tuple[list[int], list[int]]` — `(foundation_lf_indices, structural_hw_indices)`, 0-based.
- `runner.run_ocr_passes(pdf_path: str, result: dict, on_progress=None) -> dict`.

- [ ] **Step 1 — Add `inject_hardware_counts` and slim `inject_lf_data` in `aggregate.py`.**
Move the hardware-merge block (current lines ~224-240) out of `inject_lf_data` into a new function; `inject_lf_data` keeps only LF/CY/scale.

```python
def inject_lf_data(result: dict, lf_data: dict) -> dict:
    """Inject PaddleOCR footing LF + derived CY into the foundation section.
    Hardware counts are handled separately by inject_hardware_counts() so they
    survive even when footing LF is 0. Mutates result in place."""
    foundation = result.get("foundation", {})
    grand_lf = lf_data.get("grand_total_lf", 0)
    if not grand_lf:
        return result
    foundation["total_lf"] = round(grand_lf, 1)
    foundation["estimated"] = True
    for page in lf_data.get("pages", []):
        if page.get("drawing_scale") and not foundation.get("drawing_scale"):
            foundation["drawing_scale"] = page["drawing_scale"]
    if foundation.get("concrete_cubic_yards", 0) == 0:
        footing_types = foundation.get("footing_types", [])
        dims = [(ft.get("width_in", 0), ft.get("depth_in", 0))
                for ft in footing_types if ft.get("width_in") and ft.get("depth_in")]
        if dims:
            avg_w = sum(d[0] for d in dims) / len(dims)
            avg_d = sum(d[1] for d in dims) / len(dims)
            foundation["concrete_cubic_yards"] = round(grand_lf * (avg_w / 12) * (avg_d / 12) / 27, 1)
    return result


def inject_hardware_counts(result: dict, ocr_counts: dict) -> dict:
    """Merge OCR hardware callout counts into simpson_hardware + hardware_by_phase.
    Independent of footing LF (the old inject_lf_data early-returned on LF==0,
    which silently dropped the dedicated hardware pass). Mutates result in place."""
    if not ocr_counts:
        return result
    result["_ocr_hardware_counts"] = {**result.get("_ocr_hardware_counts", {}), **ocr_counts}
    result["simpson_hardware"] = _merge_hardware(result.get("simpson_hardware", []), ocr_counts)
    for raw_model, count in ocr_counts.items():
        model = _normalise_model(raw_model)
        phase = _phase_for_model(model)
        phase_list = result.get("hardware_by_phase", {}).get(phase, [])
        existing = next((h for h in phase_list if _normalise_model(h.get("model", "")) == model), None)
        if existing:
            if count > int(existing.get("qty", 0) or 0):
                existing["qty"] = count
                existing["qty_source"] = "ocr_callout"
        else:
            phase_list.append({"model": model, "qty": count, "qty_source": "ocr_callout"})
    return result
```

- [ ] **Step 2 — Add `_ocr_page_indices` + `run_ocr_passes` to `runner.py`** and import `inject_hardware_counts`.
Change the import line to: `from app.pipeline.aggregate import aggregate_results, inject_lf_data, inject_hardware_counts`. Append:

```python
_OCR_LF_CATEGORIES = ("foundation",)
_OCR_HW_CATEGORIES = ("foundation", "floor_framing", "roof_framing", "wall_framing", "framing_details")


def _ocr_page_indices(pages: list[dict]) -> tuple[list[int], list[int]]:
    """(foundation_lf_indices, structural_hw_indices), 0-based.
    LF uses foundation pages ONLY — floor/roof framing carry span/room dims that
    inflate footing LF (LHERT: 903.8 broad vs 76.8 foundation-only). Hardware
    counting uses all structural pages."""
    lf_idx = sorted({p["page"] - 1 for p in pages if p.get("category") in _OCR_LF_CATEGORIES})
    hw_idx = sorted({p["page"] - 1 for p in pages if p.get("category") in _OCR_HW_CATEGORIES})
    return lf_idx, hw_idx


def run_ocr_passes(pdf_path: str, result: dict, on_progress: ProgressCallback | None = None) -> dict:
    """PaddleOCR passes shared by CLI and web app — single source of truth, no scope drift.
    Pass 1: footing LF on foundation pages only. Pass 2: hardware callout counting on all
    structural pages. Gracefully no-ops if PaddleOCR is unavailable. Mutates result."""
    def emit(step, msg, pct):
        if on_progress:
            on_progress(step, msg, pct)
    try:
        from app.pipeline.ocr import extract_lf_from_pages, count_hardware_from_pages
    except Exception as e:
        emit("ocr", f"OCR unavailable, skipped: {e}", 95)
        return result
    lf_idx, hw_idx = _ocr_page_indices(result.get("_pages", []))
    if lf_idx:
        emit("ocr", f"Extracting footing dimensions from {len(lf_idx)} foundation page(s)...", 91)
        try:
            lf_data = extract_lf_from_pages(pdf_path, lf_idx)
            if lf_data.get("grand_total_lf"):
                inject_lf_data(result, lf_data)
                emit("ocr", f"Footing LF: {lf_data['grand_total_lf']} ft", 93)
            inject_hardware_counts(result, lf_data.get("hardware_counts", {}))
        except Exception as e:
            emit("ocr", f"LF pass skipped: {e}", 93)
    if hw_idx:
        emit("ocr", f"Counting hardware callouts on {len(hw_idx)} pages...", 94)
        try:
            hw_counts = count_hardware_from_pages(pdf_path, hw_idx)
            inject_hardware_counts(result, hw_counts)
            if hw_counts:
                emit("ocr", f"Hardware: {len(hw_counts)} types from callouts", 95)
        except Exception as e:
            emit("ocr", f"Hardware pass skipped: {e}", 95)
    return result
```

- [ ] **Step 3 — Replace `pipeline_worker`'s inline OCR block** (current lines ~188-219, the `try: from app.pipeline.ocr import ...` block) with a single call:

```python
        # PaddleOCR passes (shared with the CLI — see run_ocr_passes)
        run_ocr_passes(pdf_path, result, write_event)
```

- [ ] **Step 4 — Rewrite `test_pdf.py` OCR section.** Remove `_run_lf_extraction`, `_OCR_SCRIPT`, `_PY311`, `_OCR_CATEGORIES`, and the `import subprocess`. Replace the post-`run_pipeline_sync` OCR blocks (lines ~110-146) with:

```python
    from app.pipeline.runner import run_ocr_passes
    run_ocr_passes(pdf_path, result, on_progress)
    elapsed = time.time() - t0
```
And change the footing summary (lines ~163-169) to read from the result:
```python
    foundation = result.get("foundation", {})
    if foundation.get("total_lf") or foundation.get("concrete_cubic_yards"):
        est = " (est.)" if foundation.get("estimated") else ""
        print(f"  Footing LF:{foundation.get('total_lf', 0)} ft{est}")
        print(f"  Concrete:  {foundation.get('concrete_cubic_yards', 0)} CY{est}")
```

- [ ] **Step 5 — Unit tests** (`tests/test_extraction_fixes.py`):

```python
from app.pipeline.aggregate import inject_lf_data, inject_hardware_counts
from app.pipeline.runner import _ocr_page_indices


def _blank_result():
    return {"foundation": {"footing_types": [{"width_in": 15, "depth_in": 24}],
                            "concrete_cubic_yards": 0, "total_lf": 0, "drawing_scale": "",
                            "estimated": False},
            "simpson_hardware": [], "hardware_by_phase": {"foundation": [], "floor_framing": [],
            "wall_framing": [], "roof_framing": [], "general": []}, "_ocr_hardware_counts": {}}


def test_inject_lf_sets_total_and_cy():
    r = _blank_result()
    inject_lf_data(r, {"grand_total_lf": 76.8, "pages": [], "hardware_counts": {}})
    assert r["foundation"]["total_lf"] == 76.8
    assert r["foundation"]["estimated"] is True
    assert r["foundation"]["concrete_cubic_yards"] > 0  # 76.8 * 15/12 * 24/12 /27


def test_inject_hardware_runs_without_lf():
    # The bug: hardware was dropped when LF==0. Must now merge regardless.
    r = _blank_result()
    inject_hardware_counts(r, {"A35": 120, "HDU4": 8})
    models = {h["model"]: h for h in r["simpson_hardware"]}
    assert models["A35"]["qty"] == 120
    assert models["HDU4"]["qty"] == 8
    assert "A35" in [h["model"] for h in r["hardware_by_phase"]["wall_framing"]]


def test_ocr_page_indices_lf_is_foundation_only():
    pages = [{"page": 1, "category": "foundation"},
             {"page": 2, "category": "floor_framing"},
             {"page": 3, "category": "roof_framing"},
             {"page": 4, "category": "framing_details"}]
    lf_idx, hw_idx = _ocr_page_indices(pages)
    assert lf_idx == [0]                       # foundation only
    assert hw_idx == [0, 1, 2, 3]              # all structural
```

- [ ] **Step 6 — Run unit tests.** `cd app/backend && PYTHONPATH=. ../../venv/melvin311/bin/python -m pytest tests/test_extraction_fixes.py -v` → all pass.

- [ ] **Step 7 — Real-PDF OCR validation (Rule 4, cheap):** run `run_ocr_passes` on the captured baseline result + the LHERT PDF (OCR only, no Gemini). Expected: foundation `total_lf == 76.8` (not 903.8) and `simpson_hardware` contains ocr_callout counts. (Script in scratchpad.)

---

## Task 2: Project name/address from structural title-block pages

**Why:** `_most_common` picks the value on the most pages. LHERT: "8004 GONZAGA AVE" on 5 early pages (no SE) out-votes the correct "3333 Cabrillo Blvd" on 4 pages — 3 of which are the structural title sheets carrying the SE. Verified per-page in the baseline.

**Files:** Modify `aggregate.py`; Test `tests/test_extraction_fixes.py`.

- [ ] **Step 1 — Collect per-page project records** instead of flat lists. In `aggregate_results`, replace the four `proj_*` lists with one `proj_records: list[dict] = []`, and in the `schedules` branch replace the four `proj_*.append(...)` lines with:
```python
            rec = {"name": (data.get("project_name") or "").strip(),
                   "address": (data.get("project_address") or "").strip(),
                   "architect": (data.get("architect") or "").strip(),
                   "structural_engineer": (data.get("structural_engineer") or "").strip()}
            if any(rec.values()):
                proj_records.append(rec)
```

- [ ] **Step 2 — Add resolver** near `_most_common`:
```python
def _resolve_project_field(records: list[dict], field: str) -> str:
    """Most-common value, preferring records that also carry a structural_engineer
    (true structural title-block pages). Early pages (vicinity maps, adjacent-
    property notes, civil sheets) often show a different address but no SE and
    would otherwise win on raw frequency. Falls back to all records."""
    title_block = [r for r in records if r.get("structural_engineer")]
    pool = title_block if any(r.get(field) for r in title_block) else records
    return _most_common([r.get(field, "") for r in pool])
```

- [ ] **Step 3 — Resolve fields.** Replace the four resolution lines with:
```python
    result["project"]["name"]                = _resolve_project_field(proj_records, "name")
    result["project"]["address"]             = _resolve_project_field(proj_records, "address")
    result["project"]["architect"]           = _most_common([r["architect"] for r in proj_records])
    result["project"]["structural_engineer"] = _most_common([r["structural_engineer"] for r in proj_records])
```

- [ ] **Step 4 — Unit test** (append to `tests/test_extraction_fixes.py`):
```python
from app.pipeline.aggregate import _resolve_project_field

def test_address_prefers_titleblock_with_se():
    records = [  # mirrors LHERT baseline: wrong addr on more pages, no SE
        {"name": "LHERT-SONG", "address": "8004 GONZAGA AVE", "structural_engineer": ""},
        {"name": "LHERT-SONG", "address": "8004 GONZAGA AVE", "structural_engineer": ""},
        {"name": "LHERT-SONG", "address": "8004 GONZAGA AVE", "structural_engineer": ""},
        {"name": "LHERT-SONG", "address": "3333 CABRILLO BLVD", "structural_engineer": ""},
        {"name": "Lhert-Song", "address": "3333 Cabrillo Blvd", "structural_engineer": "Ashley & Vance"},
        {"name": "Lhert-Song", "address": "3333 Cabrillo Blvd", "structural_engineer": "Sean Galbreath"},
        {"name": "Lhert-Song", "address": "3333 Cabrillo Blvd", "structural_engineer": "Sean Galbreath SE"},
    ]
    assert "CABRILLO" in _resolve_project_field(records, "address").upper()
    assert "GONZAGA" not in _resolve_project_field(records, "address").upper()

def test_address_fallback_when_no_se():
    records = [{"name": "X", "address": "100 A ST", "structural_engineer": ""},
              {"name": "X", "address": "100 A ST", "structural_engineer": ""},
              {"name": "X", "address": "200 B ST", "structural_engineer": ""}]
    assert _resolve_project_field(records, "address") == "100 A ST"  # most-common fallback
```

- [ ] **Step 5 — Run tests** (same pytest command) → pass.

- [ ] **Step 6 — Real-data validation (Rule 4, no API):** re-run `aggregate_results` on the captured baseline's `_pages` and assert `project.address` now contains "Cabrillo". (Script in scratchpad.)

---

## Final validation & commit
- [ ] Run full unit suite: `pytest tests/test_extraction_fixes.py -v` (+ existing `tests/` to confirm no regressions).
- [ ] Real-data checks (Steps 1.7 + 2.6) pass: LF 76.8, address Cabrillo, hardware counts present.
- [ ] Commit code + tests + this plan + the analysis docs. Stage explicit paths only (no `-A`). Co-author trailer.

## Out of scope (documented follow-ups — `docs/analysis-2026-06-20/05`)
PaddleOCR pin-hardening (constraints file) · sqft fallback honesty (B-SQFT) · noise filter → data-layer allowlist (F-8) · native JSON mode (E1) · tiling/≥200 DPI (E2) · PP-Structure table recognition (E3) · model upgrade Gemini-2.5-Pro/Claude (R2) · counting via detection/outsource (Q1). These need network (PP-Structure models), cost decisions, or schema cascade and belong in later increments.

## Self-review
- Spec coverage: B-LF (Task 1 scope), dead hardware pass (Task 1 Step 1/2), B-A (Task 2) — all covered.
- Placeholder scan: all steps contain real code/commands. ✓
- Type consistency: `inject_hardware_counts`/`inject_lf_data`/`_ocr_page_indices`/`run_ocr_passes`/`_resolve_project_field` signatures consistent across runner.py call sites and tests. ✓

---

# Increment 2 — Native JSON mode (E1)

**Goal:** Eliminate avoidable `parse_error`s/refusals-as-text by using each provider's native structured-output mode instead of relying on a free-text "return JSON" instruction + brittle fence-stripping.

**Why:** `extract.py` calls GPT-4o (`:32`, `:126`) and Gemini (`:55`, `:86`) without `response_format`/`response_mime_type`; `_parse_response` then fails on any prose around the JSON → page lost (documented ~5–8% parse-error rate). Native JSON mode forces valid JSON. The OpenAI json_object requirement ("messages must contain 'json'") is satisfied — SYSTEM_PROMPT says "Return valid JSON only" and every prompt embeds a JSON schema. `_parse_response` stays as a defensive fallback. No schema change.

**Files:** Modify `app/backend/app/pipeline/extract.py` (4 call sites).

- [ ] **Step 1 — GPT-4o text** (`extract_text`): add `response_format={"type": "json_object"},` to the `client.chat.completions.create(...)` call.
- [ ] **Step 2 — GPT-4o vision** (`extract_vision`): add `response_format={"type": "json_object"},` to the create call.
- [ ] **Step 3 — Gemini vision** (`extract_vision_gemini`): add `response_mime_type="application/json"` to the `GenerationConfig(...)`.
- [ ] **Step 4 — Gemini dimensions** (`extract_dimensions_gemini`): add `response_mime_type="application/json"` to its `GenerationConfig(...)`.
- [ ] **Step 5 — Validate (Rule 4, cheap, OpenAI only — no Gemini quota):** run `extract_text` on a real LHERT schedule page's text and `extract_vision` on one rendered page; assert no `parse_error` and a populated dict. Gemini JSON mode is standard and will be exercised on the next full run (quota-bound today).
- [ ] **Step 6 — Commit** (extract.py only; co-author trailer).

**Risk:** minimal — both modes are GA for the models in use (gpt-4o, gemini-2.5-flash) and only constrain output to valid JSON, which the pipeline already expects.
