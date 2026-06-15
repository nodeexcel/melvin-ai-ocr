"""
Labor cost estimation — multiplies preliminary quantities by Melvin's own rates.
All outputs marked estimated=True. No output if rates are empty or quantities are zero.
"""


_RATE_LABELS = {
    "wall_stud_labor":       ("Wall Studs",          "pcs"),
    "plywood_subfloor_labor":("Subfloor Plywood",    "sheets"),
    "plywood_sheathing_labor":("Wall Sheathing",     "sheets"),
    "tji_joist_labor":       ("TJI Floor Joists",    "pcs"),
    "concrete_labor":        ("Concrete (pour+finish)","CY"),
    "excavation_labor":      ("Excavation",          "LF"),
    "hardware_install":      ("Hardware Installation","pcs"),
}


def _qty_from_result(result: dict) -> dict:
    """Pull the quantities we can price from the pipeline result."""
    qty = result.get("quantities", {})
    foundation = result.get("foundation", {})
    hw = result.get("simpson_hardware", [])

    # Wall studs — sum all wall types
    studs = sum(item.get("estimated_qty", 0) for item in qty.get("wall_framing", []))

    # Plywood by type
    subfloor = next((i.get("estimated_qty", 0) for i in qty.get("plywood", [])
                     if "subfloor" in i.get("description", "").lower()), 0)
    sheathing = next((i.get("estimated_qty", 0) for i in qty.get("plywood", [])
                      if "sheathing" in i.get("description", "").lower()), 0)

    # TJI joists
    tji = sum(item.get("estimated_qty", 0) for item in qty.get("floor_framing", [])
              if "tji" in item.get("size", "").lower() or "i-joist" in item.get("size", "").lower())

    # Concrete CY
    concrete_cy = foundation.get("concrete_cubic_yards") or 0

    # Foundation LF for excavation
    excavation_lf = foundation.get("total_lf") or 0

    # Hardware piece count (with qty > 0)
    hw_pieces = sum(
        (h.get("qty") or h.get("qty_mentioned") or 0)
        for h in hw
        if h.get("model")
    )

    return {
        "wall_stud_labor":        studs,
        "plywood_subfloor_labor": subfloor,
        "plywood_sheathing_labor":sheathing,
        "tji_joist_labor":        tji,
        "concrete_labor":         concrete_cy,
        "excavation_labor":       excavation_lf,
        "hardware_install":       hw_pieces,
    }


def estimate_costs(result: dict, rates: dict) -> dict:
    """
    Takes the aggregated pipeline result + Melvin's rate sheet.
    Returns a cost estimate dict with line items and total.
    Returns {} if rates are empty or no priceable quantities exist.
    """
    if not rates:
        return {}

    quantities = _qty_from_result(result)
    line_items = []

    for key, (label, unit) in _RATE_LABELS.items():
        rate = rates.get(key, 0)
        qty = quantities.get(key, 0)
        if rate and qty:
            cost = round(rate * qty, 2)
            line_items.append({
                "description": label,
                "qty": qty,
                "unit": unit,
                "rate": rate,
                "cost": cost,
            })

    if not line_items:
        return {}

    return {
        "estimated": True,
        "note": "Preliminary labor estimate — verify before quoting",
        "line_items": line_items,
        "total": round(sum(i["cost"] for i in line_items), 2),
    }
