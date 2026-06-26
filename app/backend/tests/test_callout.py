"""Tests for the text-layer detail-callout detector (callout.py).

Unit tests use synthetic text only — no PDF file required.
Integration tests hit the 8603 Rugby PDF and are skipped if the file is absent.
"""

import pytest
from collections import defaultdict

from app.pipeline.callout import (
    _extract_tokens,
    _scan_tokens,
    detect_callouts_text_layer,
    has_text_layer,
    summarise_callouts,
)

# ── helpers ────────────────────────────────────────────────────────────────────

def _counts():
    """Return a fresh defaultdict matching the internal counts shape."""
    return defaultdict(lambda: {"count": 0, "typical": False, "pages": []})


def _scan(text: str, page_num: int = 1) -> dict:
    c = _counts()
    _scan_tokens(_extract_tokens(text), page_num, c)
    return dict(c)


# ── token extraction ────────────────────────────────────────────────────────────

def test_extract_tokens_splits_newlines():
    tokens = _extract_tokens("SD3\n1\nSD3\n2\n")
    assert tokens == ["SD3", "1", "SD3", "2"]


def test_extract_tokens_strips_blank_lines():
    tokens = _extract_tokens("SD2\n\n7A\n")
    assert tokens == ["SD2", "7A"]


# ── adjacent format: SDx then num ──────────────────────────────────────────────

def test_adjacent_basic():
    c = _scan("SD3\n1")
    assert c[("1", "SD3")]["count"] == 1


def test_adjacent_count_accumulates():
    # four SD3/1 callouts, two SD3/2
    text = "\n".join(["SD3", "1", "SD3", "1", "SD3", "1", "SD3", "1", "SD3", "2", "SD3", "2"])
    c = _scan(text)
    assert c[("1", "SD3")]["count"] == 4
    assert c[("2", "SD3")]["count"] == 2


def test_adjacent_typ_flag():
    c = _scan("SD3\n16 TYP.")
    info = c[("16", "SD3")]
    assert info["count"] == 1
    assert info["typical"] is True


def test_adjacent_typ_dot_flag():
    c = _scan("SD3\n20 TYP.")
    assert c[("20", "SD3")]["typical"] is True


def test_adjacent_no_typ_by_default():
    c = _scan("SD2\n1")
    assert c[("1", "SD2")]["typical"] is False


def test_adjacent_alpha_suffix():
    c = _scan("SD2\n7A")
    assert c[("7A", "SD2")]["count"] == 1


def test_adjacent_with_trailing_annotation():
    # Detail number token has structural annotation after it — still valid callout.
    c = _scan("SD4\n20 4x12 HDR")
    assert c[("20", "SD4")]["count"] == 1


def test_adjacent_annotation_preserves_typ():
    c = _scan("SD2\n4 TYP. 2x12 F.J.")
    info = c[("4", "SD2")]
    assert info["count"] == 1
    assert info["typical"] is True


# ── inline format: "SDx num" single token ──────────────────────────────────────

def test_inline_basic():
    c = _scan("SD1 2")
    assert c[("2", "SD1")]["count"] == 1


def test_inline_alpha():
    c = _scan("SD2 7A")
    assert c[("7A", "SD2")]["count"] == 1


def test_inline_typ():
    c = _scan("SD1 5 TYP.")
    assert c[("5", "SD1")]["typical"] is True


# ── non-matches (false-positive guard) ─────────────────────────────────────────

def test_digit_start_non_sheet_not_counted():
    # "4x4 POST" should NOT match as a sheet or detail.
    c = _scan("4x4 POST\n2x12 F.J.")
    assert len(c) == 0


def test_span_annotation_not_counted():
    # "3 L=14'-0"" follows no sheet ID — should not appear.
    c = _scan("3 L=14'-0\"")
    assert len(c) == 0


def test_bare_number_without_sheet_not_counted():
    c = _scan("HDUE9\n1\n2")
    assert len(c) == 0


def test_non_sheet_prefix_not_counted():
    # "F2", "F3" are footing labels, not sheet IDs.
    c = _scan("F2\n1\nF3\n2")
    assert len(c) == 0


def test_hfx_not_sheet():
    c = _scan("HFX-18x9\n1")
    assert len(c) == 0


# ── case insensitivity ──────────────────────────────────────────────────────────

def test_lowercase_sheet_normalised():
    c = _scan("sd3\n1")
    assert ("1", "SD3") in c


# ── multi-page tracking ─────────────────────────────────────────────────────────

def test_pages_list_updated():
    c = _counts()
    _scan_tokens(_extract_tokens("SD2\n1"), 3, c)
    _scan_tokens(_extract_tokens("SD2\n1"), 4, c)
    assert sorted(c[("1", "SD2")]["pages"]) == [3, 4]


def test_pages_list_no_duplicates():
    c = _counts()
    _scan_tokens(_extract_tokens("SD2\n1\nSD2\n2"), 3, c)
    _scan_tokens(_extract_tokens("SD2\n1"), 3, c)   # same page twice
    assert c[("1", "SD2")]["pages"] == [3]           # no dup


# ── summarise_callouts ──────────────────────────────────────────────────────────

def test_summarise_totals():
    text = "\n".join(["SD1", "5"] * 7 + ["SD2", "1"] * 3)
    c = _scan(text)
    s = summarise_callouts(c)
    assert s["total_markers"] == 10
    assert s["unique_pairs"] == 2
    assert s["by_sheet"]["SD1"] == 7
    assert s["by_sheet"]["SD2"] == 3


def test_summarise_typical_pairs():
    text = "SD3\n16 TYP.\nSD3\n1\nSD1\n5 TYP."
    c = _scan(text)
    s = summarise_callouts(c)
    assert ("16", "SD3") in s["typical_pairs"]
    assert ("5", "SD1") in s["typical_pairs"]
    assert ("1", "SD3") not in s["typical_pairs"]


# ── integration tests (skip if PDF absent) ────────────────────────────────────

RUGBY_PDF = "/home/lap-68/Downloads/(DRAFT)_8603 Rugby Dr, West Hollywood - Str Plans_5-28-26.pdf"

@pytest.mark.integration
def test_rugby_plan_pages_have_callouts():
    """Plan pages 3+4 (0-based 2+3) should have SD1/SD2/SD3 callouts."""
    pytest.importorskip("pypdfium2")
    import os
    if not os.path.exists(RUGBY_PDF):
        pytest.skip("Rugby PDF not found")

    counts = detect_callouts_text_layer(RUGBY_PDF, page_indices=[2, 3])
    s = summarise_callouts(counts)

    # Verify all three sheets detected
    assert "SD1" in s["by_sheet"], "SD1 callouts expected on plan pages"
    assert "SD2" in s["by_sheet"], "SD2 callouts expected on plan pages"
    assert "SD3" in s["by_sheet"], "SD3 callouts expected on plan pages"

    # Counts from manual review of the text layer
    assert s["by_sheet"]["SD3"] >= 20, f"Expected ≥20 SD3 callouts, got {s['by_sheet']['SD3']}"
    assert s["by_sheet"]["SD2"] >= 15, f"Expected ≥15 SD2 callouts, got {s['by_sheet']['SD2']}"
    # Plan pages 3+4 only (detail sheet excluded): 8 SD1 markers verified manually
    assert s["by_sheet"]["SD1"] >= 8, f"Expected ≥8 SD1 callouts from plan pages only, got {s['by_sheet']['SD1']}"

    # TYP. detection works
    typical_sheets = {sheet for _, sheet in s["typical_pairs"]}
    assert "SD3" in typical_sheets, "SD3 has known TYP. callouts (detail 16, 20)"


@pytest.mark.integration
def test_rugby_detail_page_excluded():
    """Running the detector on just the detail sheet (page 5, idx 4) must produce
    a count, but when excluded from a plan-page-only run the plan-page count is lower."""
    pytest.importorskip("pypdfium2")
    import os
    if not os.path.exists(RUGBY_PDF):
        pytest.skip("Rugby PDF not found")

    plan_only = detect_callouts_text_layer(RUGBY_PDF, page_indices=[2, 3])
    with_detail = detect_callouts_text_layer(RUGBY_PDF, page_indices=[2, 3, 4])

    plan_total = sum(v["count"] for v in plan_only.values())
    detail_total = sum(v["count"] for v in with_detail.values())

    # Including page 5 (detail sheet) inflates the count — confirms that
    # the caller must filter by page category to avoid overcounting.
    assert detail_total > plan_total, (
        "Including the detail sheet page should add extra 'callouts' "
        "(detail-box headers on the sheet itself)"
    )


@pytest.mark.integration
def test_rugby_has_text_layer():
    """Rugby is a CAD PDF — its plan pages must have a text layer."""
    pytest.importorskip("pypdfium2")
    import os
    if not os.path.exists(RUGBY_PDF):
        pytest.skip("Rugby PDF not found")

    assert has_text_layer(RUGBY_PDF, page_index=2), "Page 3 (foundation plan) expected to have text layer"
    assert has_text_layer(RUGBY_PDF, page_index=3), "Page 4 (framing plan) expected to have text layer"


@pytest.mark.integration
def test_detect_callouts_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        detect_callouts_text_layer("/nonexistent/path.pdf", page_indices=[0])
