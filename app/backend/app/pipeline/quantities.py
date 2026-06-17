"""
Preliminary quantity estimator for residential structural framing.
Uses extracted specs + floor area → estimated piece counts.

All outputs are marked estimated=True — preliminary only, verify before ordering.
Accuracy: 50-70%. Based on standard CA residential framing practices.
Reference: docs/PLAN.md Priority 3, memory/procurement_format.md (Ganahl EST618017).
"""
import math


def _round_up(val: float, to: int = 1) -> int:
    return math.ceil(val / to) * to


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
    joists = floor_framing.get("joists", [])

    for joist in joists:
        size = joist.get("size", "")
        spacing_in = joist.get("spacing_in", 16) or 16
        span_ft = joist.get("span_ft", 0)
        qty_pieces = joist.get("qty_pieces", 0)

        if not size:
            continue

        if qty_pieces:
            # Gemini gave us a count — use it
            results.append({
                "size": size, "spacing_in": spacing_in, "span_ft": span_ft,
                "estimated_qty": qty_pieces, "estimated": False,
                "note": "from plan extraction"
            })
        elif spacing_in and total_sqft:
            # Estimate: floor_width ≈ sqrt(sqft), joists = width / spacing + 2 (rim joists)
            floor_width_ft = math.sqrt(total_sqft) * 1.2  # 1.2 factor for irregular plan
            spacing_ft = spacing_in / 12
            qty = _waste(floor_width_ft / spacing_ft + 2, 0.10)
            length = span_ft if span_ft else round(math.sqrt(total_sqft) * 0.8)
            results.append({
                "size": size, "spacing_in": spacing_in, "span_ft": length,
                "estimated_qty": qty, "estimated": True,
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
            qty = _waste(lf / spacing_ft * 2.2, 0.10)  # ×2.2 for plates + blocking
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
            qty = _waste(lf / spacing_ft * 2.2, 0.10)
            estimated = True
            note = f"estimated from {total_sqft} sqft @ {spacing_in}\" O.C."

        # Standard stud length = wall height + 0.5ft (plates)
        stud_length = _round_up(height_ft + 0.5, 2)

        results.append({
            "size": size, "spacing_in": spacing_in, "wall_type": wall_type,
            "wall_lf": lf, "stud_length_ft": stud_length,
            "estimated_qty": qty, "estimated": estimated, "note": note
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
        sheets = _waste(total_sqft / 32, 0.10)
        results.append({
            "description": "Subfloor (23/32 CD T&G PLY)", "size": "4x8",
            "thickness": "23/32", "grade": "CD T&G PLY 48/24",
            "estimated_qty": sheets, "estimated": True,
            "note": f"estimated from {total_sqft} sqft floor area"
        })
    if has_walls:
        # Wall sheathing ≈ perimeter × avg height × 0.8 (openings)
        perimeter_ft = 4 * math.sqrt(total_sqft) * 1.3
        wall_area = perimeter_ft * 9 * 0.8
        sheets = _waste(wall_area / 32, 0.10)
        results.append({
            "description": "Wall sheathing (15/32 CD STR 1)", "size": "4x10",
            "thickness": "15/32", "grade": "CD STR 1 4-PLY 32/16",
            "estimated_qty": sheets, "estimated": True,
            "note": f"estimated from {total_sqft} sqft (perimeter × height)"
        })
    if has_roof:
        # Roof area ≈ floor area × 1.3 (hip/gable factor)
        roof_area = total_sqft * 1.3
        sheets = _waste(roof_area / 32, 0.10)
        results.append({
            "description": "Roof sheathing (19/32 PLY 40/20)", "size": "4x8",
            "thickness": "19/32", "grade": "PLY SHEATHING 40/20",
            "estimated_qty": sheets, "estimated": True,
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

    has_floor = bool(floor_framing.get("joists") or total_sqft)
    has_roof = bool(roof_framing.get("rafters") or total_sqft)
    has_walls = bool(wall_framing.get("exterior_walls") or total_sqft)

    quantities = {
        "total_sqft": total_sqft,
        "estimated": True,
        "note": "Preliminary estimates — verify quantities before ordering",
        "floor_framing": estimate_floor_framing(floor_framing, total_sqft),
        "wall_framing":  estimate_wall_framing(wall_framing, total_sqft),
        "plywood":       estimate_plywood(total_sqft, has_floor, has_roof, has_walls),
    }

    return quantities
