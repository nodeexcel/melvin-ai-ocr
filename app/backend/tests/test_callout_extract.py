"""Tests for stage-4 callout hardware extractor (callout_extract.py).

Unit tests use mocks only — no API calls, no real PDFs.
Integration tests require the Rugby PDF and GOOGLE_API_KEY in env.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.callout_extract import _validate_hw, rollup_hardware


# ── _validate_hw ─────────────────────────────────────────────────────────────────

def test_validate_hw_filters_noise():
    raw = [
        {"model": "HDU4", "qty_mentioned": 2},
        {"model": "PSL", "qty_mentioned": 0},   # lumber grade — noise
        {"model": "lus", "qty_mentioned": 0},   # bare prefix — noise
        {"model": "TIE", "qty_mentioned": 1},   # generic word — noise
        {"model": "MSTC28", "qty_mentioned": 4},
    ]
    out = _validate_hw(raw)
    models = {x["model"] for x in out}
    assert "HDU4" in models
    assert "MSTC28" in models
    assert "PSL" not in models
    assert "lus" not in models
    assert "TIE" not in models


def test_validate_hw_normalises_model():
    raw = [{"model": "Simpson HDU5", "qty_mentioned": 1}]
    out = _validate_hw(raw)
    assert out[0]["model"] == "HDU5"


def test_validate_hw_dedup_keeps_highest_qty():
    raw = [
        {"model": "A35", "qty_mentioned": 0},
        {"model": "A35", "qty_mentioned": 12},
        {"model": "a35", "qty_mentioned": 5},
    ]
    out = _validate_hw(raw)
    assert len(out) == 1
    assert out[0]["qty_per_detail"] == 12


def test_validate_hw_empty_input():
    assert _validate_hw([]) == []


def test_validate_hw_malformed_entries():
    raw = [None, "not-a-dict", {"model": "HDU4"}, {"qty_mentioned": 3}]
    # Should not raise; real models get through, malformed items skipped
    out = _validate_hw(raw)
    assert all(isinstance(x, dict) for x in out)


# ── rollup_hardware ───────────────────────────────────────────────────────────────

def test_rollup_sums_across_details():
    detail_results = [
        {
            "detail_num": "1", "sheet_id": "SD1", "callout_count": 5,
            "total_hardware": [
                {"model": "HDU4", "total_qty": 10, "provenance": "callout(1/SD1 ×5)"},
                {"model": "A35",  "total_qty": 5,  "provenance": "callout(1/SD1 ×5)"},
            ],
        },
        {
            "detail_num": "2", "sheet_id": "SD1", "callout_count": 3,
            "total_hardware": [
                {"model": "HDU4", "total_qty": 6,  "provenance": "callout(2/SD1 ×3)"},
                {"model": "LUS28","total_qty": 3,  "provenance": "callout(2/SD1 ×3)"},
            ],
        },
    ]
    rolled = rollup_hardware(detail_results)
    by = {x["model"]: x for x in rolled}
    assert by["HDU4"]["total_qty"] == 16    # 10 + 6
    assert by["A35"]["total_qty"] == 5
    assert by["LUS28"]["total_qty"] == 3
    # All entries have estimated=True
    assert all(x["estimated"] is True for x in rolled)


def test_rollup_provenance_combines():
    detail_results = [
        {"total_hardware": [{"model": "A35", "total_qty": 5, "provenance": "callout(1/SD1 ×5)"}]},
        {"total_hardware": [{"model": "A35", "total_qty": 3, "provenance": "callout(2/SD1 ×3)"}]},
    ]
    rolled = rollup_hardware(detail_results)
    assert len(rolled) == 1
    prov = rolled[0]["provenance"]
    assert "1/SD1" in prov and "2/SD1" in prov


def test_rollup_empty_input():
    assert rollup_hardware([]) == []


def test_rollup_skips_empty_details():
    detail_results = [
        {"total_hardware": []},
        {"total_hardware": [{"model": "HDU5", "total_qty": 4, "provenance": "p"}]},
    ]
    rolled = rollup_hardware(detail_results)
    assert len(rolled) == 1 and rolled[0]["model"] == "HDU5"


# ── extract_detail_hardware (mocked) ─────────────────────────────────────────────

def _make_record(resolved: bool, count: int = 3) -> dict:
    base = {
        "detail_num": "1",
        "sheet_id": "SD1",
        "callout_count": count,
        "typical": False,
        "callout_pages": [2],
        "resolved": resolved,
        "detail_page_index": 4 if resolved else None,
        "crop_bbox": (100.0, 200.0, 500.0, 600.0) if resolved else None,
        "header_bbox": (100.0, 590.0, 200.0, 600.0) if resolved else None,
        "header_text": "SD1 1" if resolved else None,
    }
    return base


def test_extract_unresolved_passthrough(tmp_path):
    """Unresolved records get modality='unresolved' with empty hardware."""
    fake_pdf = tmp_path / "dummy.pdf"
    fake_pdf.write_bytes(b"%PDF")

    rec = _make_record(resolved=False)

    # Patch pdfium to avoid real file parsing
    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=10)

    with patch("app.pipeline.callout_extract.pdfium.PdfDocument", return_value=mock_doc):
        from app.pipeline.callout_extract import extract_detail_hardware
        results = extract_detail_hardware("FAKE_KEY", str(fake_pdf), [rec])

    assert len(results) == 1
    r = results[0]
    assert r["modality"] == "unresolved"
    assert r["per_detail_hardware"] == []
    assert r["total_hardware"] == []
    assert r["resolved"] is False


def test_extract_text_path_used_when_enough_chars(tmp_path):
    """When crop text has ≥ MIN_TEXT_CHARS, text path is taken (not vision)."""
    fake_pdf = tmp_path / "dummy.pdf"
    fake_pdf.write_bytes(b"%PDF")

    rec = _make_record(resolved=True, count=5)

    mock_textpage = MagicMock()
    mock_textpage.get_text_bounded.return_value = "HDU4 post base A35 joist hanger x some framing note"
    mock_page = MagicMock()
    mock_page.get_textpage.return_value = mock_textpage
    mock_page.get_size.return_value = (2592.0, 1728.0)
    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=10)
    mock_doc.__getitem__ = MagicMock(return_value=mock_page)

    gemini_response = '{"hardware": [{"model": "HDU4", "qty_mentioned": 1}, {"model": "A35", "qty_mentioned": 2}]}'

    with patch("app.pipeline.callout_extract.pdfium.PdfDocument", return_value=mock_doc), \
         patch("app.pipeline.callout_extract._call_gemini_text", return_value=[
             {"model": "HDU4", "qty_mentioned": 1},
             {"model": "A35", "qty_mentioned": 2},
         ]) as mock_text, \
         patch("app.pipeline.callout_extract._call_gemini_vision") as mock_vision:

        from app.pipeline.callout_extract import extract_detail_hardware
        results = extract_detail_hardware("FAKE_KEY", str(fake_pdf), [rec])

    assert mock_text.called
    assert not mock_vision.called

    r = results[0]
    assert r["modality"] == "text_layer"
    by = {h["model"]: h for h in r["total_hardware"]}
    assert "HDU4" in by
    assert by["HDU4"]["total_qty"] == 5     # 1 per detail × 5 callouts
    assert by["A35"]["total_qty"] == 10     # 2 per detail × 5 callouts


def test_extract_vision_path_used_when_no_text(tmp_path):
    """When crop text is short, vision path is taken."""
    fake_pdf = tmp_path / "dummy.pdf"
    fake_pdf.write_bytes(b"%PDF")

    rec = _make_record(resolved=True, count=2)

    mock_textpage = MagicMock()
    mock_textpage.get_text_bounded.return_value = ""   # no text → vision path
    mock_page = MagicMock()
    mock_page.get_textpage.return_value = mock_textpage
    mock_page.get_size.return_value = (2592.0, 1728.0)
    mock_doc = MagicMock()
    mock_doc.__len__ = MagicMock(return_value=10)
    mock_doc.__getitem__ = MagicMock(return_value=mock_page)

    with patch("app.pipeline.callout_extract.pdfium.PdfDocument", return_value=mock_doc), \
         patch("app.pipeline.callout_extract._call_gemini_text") as mock_text, \
         patch("app.pipeline.callout_extract._call_gemini_vision", return_value=[
             {"model": "LUS28", "qty_mentioned": 0},
         ]) as mock_vision, \
         patch("app.pipeline.callout_extract.render_crop", return_value=MagicMock()):

        from app.pipeline.callout_extract import extract_detail_hardware
        results = extract_detail_hardware("FAKE_KEY", str(fake_pdf), [rec])

    assert mock_vision.called
    assert not mock_text.called

    r = results[0]
    assert r["modality"] == "vision"
    by = {h["model"]: h for h in r["total_hardware"]}
    assert "LUS28" in by
    assert by["LUS28"]["total_qty"] == 2    # qty_per_detail=0 → defaults to 1 × 2 callouts


# ── integration (skip if no PDF or key) ──────────────────────────────────────────

RUGBY_PDF = "/home/lap-68/Downloads/(DRAFT)_8603 Rugby Dr, West Hollywood - Str Plans_5-28-26.pdf"


@pytest.mark.integration
def test_extract_rugby_text_path():
    """Full stage 2→3→4 on Rugby PDF using text-layer path (no vision)."""
    if not os.path.exists(RUGBY_PDF):
        pytest.skip("Rugby PDF not found")
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set")

    from app.pipeline.callout import detect_callouts_text_layer
    from app.pipeline.callout_resolve import resolve_callouts
    from app.pipeline.callout_extract import extract_detail_hardware

    counts  = detect_callouts_text_layer(RUGBY_PDF, page_indices=[2, 3])
    records = resolve_callouts(RUGBY_PDF, counts, detail_page_indices=[4])
    results = extract_detail_hardware(api_key, RUGBY_PDF, records)

    assert len(results) == len(records)

    # Each result has required fields
    for r in results:
        assert "modality" in r
        assert "per_detail_hardware" in r
        assert "total_hardware" in r
        assert "resolved" in r

    resolved = [r for r in results if r["resolved"]]
    print(f"\nStage 4 results ({len(resolved)} resolved):")
    for r in resolved:
        hw = r["total_hardware"]
        print(f"  {r['detail_num']}/{r['sheet_id']}  modality={r['modality']}  hardware={[h['model'] for h in hw]}")
