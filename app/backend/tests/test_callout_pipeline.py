"""Tests for stage 5: run_callout_engine() wired into runner.py."""

from unittest.mock import patch

from app.pipeline.runner import run_callout_engine


def _make_result(categories: list[str]) -> dict:
    """Build a minimal result dict with _pages matching the given categories."""
    pages = [{"page": i + 1, "category": cat} for i, cat in enumerate(categories)]
    return {
        "_pages": pages,
        "simpson_hardware": [],
        "hardware_by_phase": {
            "foundation": [], "floor_framing": [], "wall_framing": [],
            "roof_framing": [], "general": [],
        },
        "_ocr_hardware_counts": {},
    }


def test_noop_when_no_google_key():
    result = _make_result(["foundation", "framing_details"])
    out = run_callout_engine("/fake.pdf", result, google_api_key="")
    # No hardware added, no crash
    assert out["simpson_hardware"] == []
    assert "_callout_engine" not in out


def test_noop_when_no_detail_pages():
    result = _make_result(["foundation", "floor_framing", "roof_framing"])
    out = run_callout_engine("/fake.pdf", result, google_api_key="KEY")
    assert out["simpson_hardware"] == []


def test_noop_when_no_plan_pages():
    result = _make_result(["framing_details"])
    out = run_callout_engine("/fake.pdf", result, google_api_key="KEY")
    assert out["simpson_hardware"] == []


def test_noop_when_no_callouts_found():
    result = _make_result(["foundation", "framing_details"])
    with patch("app.pipeline.callout.detect_callouts_text_layer", return_value={}):
        out = run_callout_engine("/fake.pdf", result, google_api_key="KEY")
    assert out["simpson_hardware"] == []


def test_noop_when_no_resolved():
    result = _make_result(["foundation", "framing_details"])
    counts = {("1", "SD1"): {"count": 5, "typical": False, "pages": [0]}}
    unresolved = [{"detail_num": "1", "sheet_id": "SD1", "callout_count": 5,
                   "typical": False, "callout_pages": [0], "resolved": False,
                   "detail_page_index": None, "header_bbox": None,
                   "crop_bbox": None, "header_text": None}]
    with patch("app.pipeline.callout.detect_callouts_text_layer", return_value=counts), \
         patch("app.pipeline.callout_resolve.resolve_callouts", return_value=unresolved):
        out = run_callout_engine("/fake.pdf", result, google_api_key="KEY")
    assert out["simpson_hardware"] == []
    assert out["_callout_engine"] == unresolved


def test_hardware_injected_when_resolved():
    result = _make_result(["foundation", "framing_details"])
    counts = {("1", "SD1"): {"count": 5, "typical": False, "pages": [0]}}
    resolved = [{"detail_num": "1", "sheet_id": "SD1", "callout_count": 5,
                 "typical": False, "callout_pages": [0], "resolved": True,
                 "detail_page_index": 1, "header_bbox": (0, 0, 100, 20),
                 "crop_bbox": (0, 0, 500, 500), "header_text": "SD1 1"}]
    detail_results = [{
        **resolved[0],
        "per_detail_hardware": [{"model": "HDU4", "qty_per_detail": 1}],
        "total_hardware": [{"model": "HDU4", "total_qty": 5, "provenance": "callout(1/SD1 ×5)"}],
        "modality": "text_layer",
    }]

    with patch("app.pipeline.callout.detect_callouts_text_layer", return_value=counts), \
         patch("app.pipeline.callout_resolve.resolve_callouts", return_value=resolved), \
         patch("app.pipeline.callout_extract.extract_detail_hardware", return_value=detail_results), \
         patch("app.pipeline.callout_extract.rollup_hardware", return_value=[
             {"model": "HDU4", "total_qty": 5, "estimated": True, "provenance": "callout(1/SD1 ×5)"}
         ]):
        out = run_callout_engine("/fake.pdf", result, google_api_key="KEY")

    assert any(h["model"] == "HDU4" for h in out["simpson_hardware"])
    hdu4 = next(h for h in out["simpson_hardware"] if h["model"] == "HDU4")
    assert hdu4["qty"] == 5
    assert out["_callout_engine"] == detail_results


def test_callout_engine_takes_higher_qty():
    """When OCR already has HDU4×3, callout engine HDU4×5 wins."""
    result = _make_result(["foundation", "framing_details"])
    result["simpson_hardware"] = [{"model": "HDU4", "qty": 3}]
    result["hardware_by_phase"]["foundation"] = [{"model": "HDU4", "qty": 3}]
    counts = {("1", "SD1"): {"count": 5, "typical": False, "pages": [0]}}
    resolved = [{"detail_num": "1", "sheet_id": "SD1", "callout_count": 5,
                 "typical": False, "callout_pages": [0], "resolved": True,
                 "detail_page_index": 1, "header_bbox": (0, 0, 100, 20),
                 "crop_bbox": (0, 0, 500, 500), "header_text": "SD1 1"}]
    detail_results = [{**resolved[0], "per_detail_hardware": [], "total_hardware": [
        {"model": "HDU4", "total_qty": 5, "provenance": "p"}], "modality": "text_layer"}]

    with patch("app.pipeline.callout.detect_callouts_text_layer", return_value=counts), \
         patch("app.pipeline.callout_resolve.resolve_callouts", return_value=resolved), \
         patch("app.pipeline.callout_extract.extract_detail_hardware", return_value=detail_results), \
         patch("app.pipeline.callout_extract.rollup_hardware", return_value=[
             {"model": "HDU4", "total_qty": 5, "estimated": True, "provenance": "p"}
         ]):
        out = run_callout_engine("/fake.pdf", result, google_api_key="KEY")

    hdu4 = next(h for h in out["simpson_hardware"] if h["model"] == "HDU4")
    assert hdu4["qty"] == 5   # higher of 3 vs 5


def test_progress_callback_called():
    events = []
    def cb(step, msg, pct):
        events.append((step, msg, pct))

    result = _make_result(["foundation", "framing_details"])
    with patch("app.pipeline.callout.detect_callouts_text_layer", return_value={}):
        run_callout_engine("/fake.pdf", result, google_api_key="KEY", on_progress=cb)

    assert any(e[0] == "callout_engine" for e in events)
