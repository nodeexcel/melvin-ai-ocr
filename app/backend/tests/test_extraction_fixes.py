"""Unit tests for the 2026-06-20 extraction-accuracy fixes:
- OCR LF/hardware injection split (foundation-only LF + hardware survives LF==0)
- foundation-only LF page scoping
- project name/address resolution preferring structural title-block pages
See docs/superpowers/plans/2026-06-20-extraction-accuracy-fixes.md
"""
from app.pipeline.aggregate import (
    _resolve_project_field,
    inject_hardware_counts,
    inject_lf_data,
)
from app.pipeline.runner import _ocr_page_indices


def _blank_result() -> dict:
    return {
        "foundation": {
            "footing_types": [{"width_in": 15, "depth_in": 24}],
            "concrete_cubic_yards": 0,
            "total_lf": 0,
            "drawing_scale": "",
            "estimated": False,
        },
        "simpson_hardware": [],
        "hardware_by_phase": {
            "foundation": [], "floor_framing": [], "wall_framing": [],
            "roof_framing": [], "general": [],
        },
        "_ocr_hardware_counts": {},
    }


# --- Task 1: injection split ------------------------------------------------

def test_inject_lf_sets_total_and_cy():
    r = _blank_result()
    inject_lf_data(r, {"grand_total_lf": 76.8, "pages": [], "hardware_counts": {}})
    assert r["foundation"]["total_lf"] == 76.8
    assert r["foundation"]["estimated"] is True
    # 76.8 * (15/12) * (24/12) / 27 ≈ 7.1
    assert r["foundation"]["concrete_cubic_yards"] > 0


def test_inject_lf_zero_is_noop():
    r = _blank_result()
    inject_lf_data(r, {"grand_total_lf": 0, "pages": [], "hardware_counts": {}})
    assert r["foundation"]["total_lf"] == 0


def test_inject_hardware_runs_without_lf():
    # Regression: hardware counts were dropped when footing LF == 0 (dead Pass-2).
    r = _blank_result()
    inject_hardware_counts(r, {"A35": 120, "HDU4": 8})
    models = {h["model"]: h for h in r["simpson_hardware"]}
    assert models["A35"]["qty"] == 120
    assert models["HDU4"]["qty"] == 8
    # phase assignment (existing _phase_for_model heuristic): HDU* -> foundation,
    # A35 (general-purpose angle, no specific prefix) -> general
    assert "HDU4" in [h["model"] for h in r["hardware_by_phase"]["foundation"]]
    assert "A35" in [h["model"] for h in r["hardware_by_phase"]["general"]]


def test_inject_hardware_takes_higher_count():
    r = _blank_result()
    r["simpson_hardware"] = [{"model": "A35", "qty": 5}]
    inject_hardware_counts(r, {"A35": 50})
    models = {h["model"]: h for h in r["simpson_hardware"]}
    assert models["A35"]["qty"] == 50
    assert models["A35"]["qty_source"] == "ocr_callout"


# --- Task 1: page scoping ---------------------------------------------------

def test_ocr_page_indices_lf_is_foundation_only():
    pages = [
        {"page": 1, "category": "foundation"},
        {"page": 2, "category": "floor_framing"},
        {"page": 3, "category": "roof_framing"},
        {"page": 4, "category": "framing_details"},
        {"page": 5, "category": "schedules"},
    ]
    lf_idx, hw_idx = _ocr_page_indices(pages)
    assert lf_idx == [0]                 # foundation only (no floor/roof inflation)
    assert hw_idx == [0, 1, 2, 3]        # all structural, not schedules


# --- Task 2: address resolution ---------------------------------------------

def test_address_prefers_titleblock_with_se():
    # Mirrors the LHERT baseline: wrong addr on MORE pages but no SE;
    # correct addr on the structural title-block pages that carry the SE.
    records = [
        {"name": "LHERT-SONG", "address": "8004 GONZAGA AVE", "structural_engineer": ""},
        {"name": "LHERT-SONG", "address": "8004 GONZAGA AVE", "structural_engineer": ""},
        {"name": "LHERT-SONG", "address": "8004 GONZAGA AVE", "structural_engineer": ""},
        {"name": "LHERT-SONG", "address": "3333 CABRILLO BLVD", "structural_engineer": ""},
        {"name": "Lhert-Song", "address": "3333 Cabrillo Blvd", "structural_engineer": "Ashley & Vance"},
        {"name": "Lhert-Song", "address": "3333 Cabrillo Blvd", "structural_engineer": "Sean Galbreath"},
        {"name": "Lhert-Song", "address": "3333 Cabrillo Blvd", "structural_engineer": "Sean Galbreath SE"},
    ]
    addr = _resolve_project_field(records, "address")
    assert "CABRILLO" in addr.upper()
    assert "GONZAGA" not in addr.upper()


def test_address_fallback_when_no_se():
    records = [
        {"name": "X", "address": "100 A ST", "structural_engineer": ""},
        {"name": "X", "address": "100 A ST", "structural_engineer": ""},
        {"name": "X", "address": "200 B ST", "structural_engineer": ""},
    ]
    assert _resolve_project_field(records, "address") == "100 A ST"  # most-common fallback


# --- Increment 4: hardware cleanup ------------------------------------------
from app.pipeline.hardware import is_real_model, normalise_model, clean_hardware_list


def test_is_real_model_filters_noise():
    assert is_real_model("HDU4")
    assert is_real_model("A35")
    assert is_real_model("H1")          # H-series short code allowed
    assert not is_real_model("LUTRON")  # electrical
    assert not is_real_model("UL U309") # fire-rating listing
    assert not is_real_model("")
    assert not is_real_model("B1")      # 2-char non-H drawing label
    assert not is_real_model("10d")     # nail size
    assert not is_real_model("lus")     # bare prefix-only code


def test_normalise_model_strips_simpson():
    assert normalise_model("Simpson HDU4") == "HDU4"
    assert normalise_model("HDU4") == "HDU4"
    assert normalise_model("Simpson Strong-Tie A35") == "A35"


def test_clean_hardware_dedup_keeps_highest_qty():
    items = [
        {"model": "HDU8", "qty": 0},
        {"model": "HDU8", "qty": 4, "qty_source": "ocr_callout"},
        {"model": "A35", "qty": 0},  # only-zero -> dropped
    ]
    by = {h["model"]: h for h in clean_hardware_list(items)}
    assert by["HDU8"]["qty"] == 4
    assert by["HDU8"].get("qty_source") == "ocr_callout"
    assert "A35" not in by  # pure-zero dropped


def test_clean_hardware_drops_noise_and_empty():
    items = [{"model": "LUTRON", "qty": 3}, {"model": "HDU4", "qty": 5}, {"model": "", "qty": 2}]
    assert {h["model"] for h in clean_hardware_list(items)} == {"HDU4"}


def test_clean_hardware_keep_zero_flag():
    out = clean_hardware_list([{"model": "HDU4", "qty": 0}], keep_zero=True)
    assert out and out[0]["qty"] == 0
