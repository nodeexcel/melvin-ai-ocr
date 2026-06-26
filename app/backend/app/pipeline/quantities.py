"""
Preliminary quantity estimator for residential structural framing.
Uses extracted specs + floor area → estimated piece counts.

All outputs are marked estimated=True — preliminary only, verify before ordering.
Accuracy: 50-70%. Based on standard CA residential framing practices.
Reference: docs/PLAN.md Priority 3, memory/procurement_format.md (Ganahl EST618017).
"""
import math
import re

# "RR" (Roof Rafter) abbreviation appears in CA plans. The LLM occasionally
# places rafter specs in floor_framing.joists when the framing plan page
# also shows the lower-roof members at plate level.
_RAFTER_SIZE_RE = re.compile(r'\bRR\b', re.IGNORECASE)

# Standard CA residential waste allowances.
# Applied on top of calculated base quantities — these are what to ORDER, not what installs.
WASTE_FACTORS = {
    "lumber":   0.10,   # framing lumber + studs: cuts, rejects, miscuts
    "plywood":  0.10,   # all sheathing types: edge cuts, damaged sheets
    "concrete": 0.08,   # over-pour, spills, form blow-out buffer
}


def _round_up(val: float, to: int = 1) -> int:
    return math.ceil(val / to) * to


def _with_waste(base: float, category: str = "lumber") -> dict:
    """Return base_qty, waste_pct, and estimated_qty (order quantity) as a dict."""
    pct = WASTE_FACTORS.get(category, 0.10)
    base_int = math.ceil(base)
    order_int = math.ceil(base * (1 + pct))
    return {
        "base_qty":   base_int,
        "waste_pct":  int(pct * 100),
        "estimated_qty": order_int,
    }


def _waste(qty: float, pct: float = 0.10) -> int:
    return math.ceil(qty * (1 + pct))


def estimate_floor_framing(floor_framing: dict, total_sqft: int) -> list[dict]:
    """
    Estimate floor joist quantities from spacing + floor area.
    Returns list of {size, spacing_in, estimated_qty, length_ft, estimated, note}
    Falls back to typical residential sqft when not extracted from plans.
    """
    if not total_sqft:
        total_sqft = _TYPICAL_RESIDENTIAL_SQFT

    results = []
    # Dedup by (size, spacing_in) — same spec can appear across multiple plan pages.
    # Keep entry with highest qty_pieces; fall back to first seen.
    seen: dict[tuple, dict] = {}
    for j in floor_framing.get("joists", []):
        key = (j.get("size", ""), j.get("spacing_in", 0))
        if key not in seen or j.get("qty_pieces", 0) > seen[key].get("qty_pieces", 0):
            seen[key] = j
    joists = list(seen.values())

    for joist in joists:
        size = joist.get("size", "")
        spacing_in = joist.get("spacing_in", 16) or 16
        span_ft = joist.get("span_ft", 0)
        qty_pieces = joist.get("qty_pieces", 0)

        if not size:
            continue
        if _RAFTER_SIZE_RE.search(size):
            continue  # rafter spec misclassified as joist — roof_framing handles it

        if qty_pieces:
            # Gemini gave us a count — use it (show waste on top of extracted count)
            w = _with_waste(qty_pieces, "lumber")
            results.append({
                "size": size, "spacing_in": spacing_in, "span_ft": span_ft,
                **w, "estimated": False,
                "note": "from plan extraction"
            })
        elif spacing_in and total_sqft:
            # Estimate: floor_width ≈ sqrt(sqft), joists = width / spacing + 2 (rim joists)
            floor_width_ft = math.sqrt(total_sqft) * 1.2  # 1.2 factor for irregular plan
            spacing_ft = spacing_in / 12
            base = floor_width_ft / spacing_ft + 2
            length = span_ft if span_ft else round(math.sqrt(total_sqft) * 0.8)
            w = _with_waste(base, "lumber")
            results.append({
                "size": size, "spacing_in": spacing_in, "span_ft": length,
                **w, "estimated": True,
                "note": f"estimated from {total_sqft} sqft floor area @ {spacing_in}\" O.C."
            })

    return results


_TYPICAL_RESIDENTIAL_SQFT = 2000  # fallback when sqft not extracted from plans


def estimate_wall_framing(wall_framing: dict, total_sqft: int) -> list[dict]:
    """
    Estimate stud quantities from wall linear feet + spacing.
    Returns list of {size, spacing_in, wall_type, estimated_qty, length_ft, estimated}
    Falls back to a typical residential floor area when total_sqft is unavailable.
    """
    if not total_sqft:
        total_sqft = _TYPICAL_RESIDENTIAL_SQFT

    results = []

    for wall_type, key in [("Exterior", "exterior_walls"), ("Interior", "interior_walls")]:
        walls = wall_framing.get(key) or {}
        size = walls.get("stud_size", "")
        spacing_in = walls.get("stud_spacing_in", 16) or 16
        lf = walls.get("linear_feet", 0)
        height_ft = walls.get("height_ft", 9) or 9

        if not size:
            if not total_sqft:
                continue
            # Gemini didn't extract wall framing — use CA residential defaults.
            # 2-story exterior: 2x6 @ 16" O.C.; interior: 2x4 @ 16" O.C.
            size = "2x6" if wall_type == "Exterior" else "2x4"
            spacing_in = 16
            height_ft = 9

        if lf:
            # We have LF — calculate studs
            spacing_ft = spacing_in / 12
            base = lf / spacing_ft * 2.2  # ×2.2 for plates + blocking
            estimated = False
            note = f"from {lf} LF wall"
        else:
            # Estimate LF from floor area
            if wall_type == "Exterior":
                # Perimeter ≈ 4 × sqrt(sqft) × 1.3 (irregular plan factor)
                lf = round(4 * math.sqrt(total_sqft) * 1.3)
            else:
                # Interior walls ≈ 1.5× exterior perimeter for residential
                ext_lf = walls.get("linear_feet", 0) or round(4 * math.sqrt(total_sqft) * 1.3)
                lf = round(ext_lf * 1.5)
            spacing_ft = spacing_in / 12
            base = lf / spacing_ft * 2.2
            estimated = True
            note = f"estimated from {total_sqft} sqft @ {spacing_in}\" O.C."

        # Standard stud length = wall height + 0.5ft (plates)
        stud_length = _round_up(height_ft + 0.5, 2)
        w = _with_waste(base, "lumber")

        results.append({
            "size": size, "spacing_in": spacing_in, "wall_type": wall_type,
            "wall_lf": lf, "stud_length_ft": stud_length,
            **w, "estimated": estimated, "note": note
        })

    return results


def estimate_plywood(total_sqft: int, has_floor: bool = True,
                     has_roof: bool = True, has_walls: bool = True) -> list[dict]:
    """
    Estimate plywood sheet counts from floor area.
    Standard 4×8 sheet = 32 sqft. Add 10% waste.
    Falls back to typical residential sqft when not extracted from plans.
    """
    if not total_sqft:
        total_sqft = _TYPICAL_RESIDENTIAL_SQFT

    results = []
    if has_floor:
        w = _with_waste(total_sqft / 32, "plywood")
        results.append({
            "description": "Subfloor (23/32 CD T&G PLY)", "size": "4x8",
            "thickness": "23/32", "grade": "CD T&G PLY 48/24",
            **w, "estimated": True,
            "note": f"estimated from {total_sqft} sqft floor area"
        })
    if has_walls:
        # Wall sheathing ≈ perimeter × avg height × 0.8 (openings)
        perimeter_ft = 4 * math.sqrt(total_sqft) * 1.3
        wall_area = perimeter_ft * 9 * 0.8
        w = _with_waste(wall_area / 32, "plywood")
        results.append({
            "description": "Wall sheathing (15/32 CD STR 1)", "size": "4x10",
            "thickness": "15/32", "grade": "CD STR 1 4-PLY 32/16",
            **w, "estimated": True,
            "note": f"estimated from {total_sqft} sqft (perimeter × height)"
        })
    if has_roof:
        # Roof area ≈ floor area × 1.3 (hip/gable factor)
        roof_area = total_sqft * 1.3
        w = _with_waste(roof_area / 32, "plywood")
        results.append({
            "description": "Roof sheathing (19/32 PLY 40/20)", "size": "4x8",
            "thickness": "19/32", "grade": "PLY SHEATHING 40/20",
            **w, "estimated": True,
            "note": f"estimated from {total_sqft} sqft (floor × 1.3 roof factor)"
        })

    return results


def estimate_quantities(result: dict) -> dict:
    """
    Main entry point. Takes the aggregated pipeline result dict and returns
    preliminary quantity estimates organized by phase.
    All items marked estimated=True.
    """
    project = result.get("project", {})
    total_sqft = project.get("total_sqft", 0)

    floor_framing = result.get("floor_framing", {})
    wall_framing = result.get("wall_framing", {})
    roof_framing = result.get("roof_framing", {})

    # Use fallback sqft for presence checks so sheathing always generates
    # even when the plan set didn't state a building area.
    effective_sqft = total_sqft or _TYPICAL_RESIDENTIAL_SQFT
    has_floor = bool(floor_framing.get("joists") or effective_sqft)
    has_roof  = bool(roof_framing.get("rafters")  or effective_sqft)
    has_walls = bool(wall_framing.get("exterior_walls") or effective_sqft)

    display_sqft = total_sqft or effective_sqft
    quantities = {
        "total_sqft": display_sqft,
        "estimated": True,
        "note": "Preliminary estimates — verify quantities before ordering",
        "floor_framing": estimate_floor_framing(floor_framing, total_sqft),
        "wall_framing":  estimate_wall_framing(wall_framing, total_sqft),
        "plywood":       estimate_plywood(total_sqft, has_floor, has_roof, has_walls),
    }

    # Concrete waste — 8% buffer for spills, over-pour, and form blow-out
    concrete_cy = result.get("foundation", {}).get("concrete_cubic_yards", 0) or 0
    if concrete_cy:
        w = _with_waste(concrete_cy, "concrete")
        quantities["concrete"] = {
            **w, "estimated": True,
            "note": f"{concrete_cy} CY extracted from plans + 8% waste allowance"
        }

    return quantities
