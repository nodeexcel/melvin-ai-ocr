"""Single source of truth for Simpson-hardware model normalisation, validity
filtering, and list cleaning. Used by aggregate.py (clean stored raw_json) and
report/generator.py (render-time defense). Consolidates three previously
duplicated normalise helpers + the generator's _is_real_model filter.
"""
import re


def normalise_model(m: str) -> str:
    """Normalise a hardware model for dedup: strip 'Simpson'/'Simpson Strong-Tie'
    prefixes ('Simpson H1' == 'H1') and trailing schedule footnote markers
    ('HDU11*' == 'HDU11' — the asterisk is a schedule note, not a product code)."""
    if not m:
        return ""
    m = m.strip()
    for prefix in ("Simpson Strong-Tie ", "Simpson Strong Tie ", "Simpson ", "SIMPSON "):
        if m.upper().startswith(prefix.upper()):
            m = m[len(prefix):].strip()
            break
    # Trailing footnote asterisk(s): "HDU11*", "HDU8 *" -> "HDU11", "HDU8"
    m = re.sub(r"\s*\*+\s*$", "", m).strip()
    return m


# Exact-match junk: generic words + drawing labels + incomplete prefix-only codes.
_PHASE_GENERIC = {
    "nails", "nail", "bolts", "bolt", "screws", "screw", "welds", "weld",
    "strap", "straps", "holdown", "holdowns", "strong-tie", "hardware",
    "anchor bolts", "anchor bolt", "joist hangers", "joist hanger",
    "shear plates", "shear plate", "base plate", "post cap",
    "ohagin roof vent", "ohagin", "roof vent", "sim. hanger",
    "post base", "holdown strap",
    "hss",
    # Generic fasteners
    "pan head screw", "countersunk screw", "countersunk screws",
    # Sealants / membranes / tapes
    "epdm", "epdm seal", "neoprene", "neoprene pad", "neoprene bad",
    "vhb tape", "vhb", "sealant",
    # Incomplete prefix-only codes (Gemini drops the numeric suffix).
    # Full models (LUS26, HUCQ410, ABU66) are unaffected — not exact matches.
    "lus", "hucq", "abu", "hus", "lts", "cmst", "mstc",
    # MEP / non-structural
    "hanger rod", "rod hanger", "e8005",
    # Drawing annotation labels confirmed by Melvin as non-Simpson (2026-06-19)
    "ab123", "eb456", "ea456", "ls456", "ab6", "sp789",
    # Electrical / fire-listing noise found in raw_json (2026-06-23)
    "lutron",
}

# Non-structural brand prefixes (lowercased startswith).
_NON_STRUCTURAL_BRANDS = (
    "schluter", "pemko", "astm no", "grace ", "allweather", "panda ",
    "contega", "intello", "western ", "hook #", "bronze ", "sim. ", "sim.",
    "jh", "redguard", "nds ", "zoeller", "bilco", "maxeon", "sol-ark",
    "discover ", "lutron", "leviton", "hubbel",  # electrical brands
    "ul u", "ul l",  # UL fire-rating listings (UL U309, UL L501) — not hardware
    "detail",  # "Detail 19/32/..." = plan detail-callout references, not a model
    "see detail", "see ",
    "icc", "ner-", "esr-",  # ICC-ES evaluation report numbers (NER-216, ESR-xxxx)
)

# Substrings that disqualify any model regardless of prefix/suffix.
_GENERIC_SUBSTRINGS = (
    "aluminum angle", "aluminum channel", "steel angle", "steel channel",
    "hss", "bolt", "dia.", "glazing", "stainless", "sleeve", "shock",
    " series", "screw", "pipe", "pvc", "receptacle",
)

_NAIL_PATTERN = re.compile(r"^\d+d$")   # 8d, 10d, 16d
_DIGIT_START = re.compile(r"^\d")        # 1/2" DIA. BOLTS, 3-#5
_CATALOG_START = re.compile(r"^#")       # #1301-410, #896


def is_real_model(m: str) -> bool:
    """True if `m` is a plausible structural-hardware model (not noise/label)."""
    if not m:
        return False
    # 1-2 char codes (B1/W1/S1) are drawing labels; H-series (H1/H2) are real.
    if len(m) < 3 and not m.upper().startswith("H"):
        return False
    ml = m.lower()
    if ml in _PHASE_GENERIC:
        return False
    if _NAIL_PATTERN.match(ml):
        return False
    if _DIGIT_START.match(ml):
        return False
    if _CATALOG_START.match(ml):
        return False
    if any(ml.startswith(b) for b in _NON_STRUCTURAL_BRANDS):
        return False
    if any(sub in ml for sub in _GENERIC_SUBSTRINGS):
        return False
    return True


def _qty_of(h: dict) -> int:
    try:
        return int(h.get("qty", h.get("qty_mentioned", 0)) or 0)
    except (ValueError, TypeError):
        return 0


def clean_hardware_list(items: list, keep_zero: bool = False) -> list:
    """Dedup hardware by normalised model (keep highest qty), drop noise, and —
    unless keep_zero — drop pure-zero/None-qty items. Output entries are
    {model, qty[, qty_source]}; this is what an orderable takeoff needs and
    matches what the PDF phase tables already render."""
    best: dict[str, dict] = {}
    for h in items:
        if not isinstance(h, dict):
            continue
        model = normalise_model(h.get("model", ""))
        if not is_real_model(model):
            continue
        qty = _qty_of(h)
        cur = best.get(model)
        if cur is None or qty > cur["qty"]:
            entry = {"model": model, "qty": qty}
            if h.get("qty_source"):
                entry["qty_source"] = h["qty_source"]
            best[model] = entry
    return [e for e in best.values() if e["qty"] > 0 or keep_zero]


def clean_result_hardware(result: dict) -> dict:
    """Clean the hardware lists in an aggregated result in place: the flat
    simpson_hardware list and every hardware_by_phase bucket. Idempotent."""
    if isinstance(result.get("simpson_hardware"), list):
        result["simpson_hardware"] = clean_hardware_list(result["simpson_hardware"])
    hbp = result.get("hardware_by_phase")
    if isinstance(hbp, dict):
        for phase, items in hbp.items():
            if isinstance(items, list):
                hbp[phase] = clean_hardware_list(items)
    return result
