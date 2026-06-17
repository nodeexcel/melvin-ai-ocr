"""
Labor and equipment cost estimation — multiplies extracted quantities by Melvin's rates.
All outputs marked estimated=True. Returns {} if rates are empty or no quantities exist.
"""
import math


_RATE_LABELS = {
    # Labor
    "wall_stud_labor":        ("Wall Studs (labor)",          "pcs"),
    "plywood_subfloor_labor": ("Subfloor Plywood (labor)",    "sheets"),
    "plywood_sheathing_labor":("Wall Sheathing (labor)",      "sheets"),
    "tji_joist_labor":        ("TJI Floor Joists (labor)",    "pcs"),
    "concrete_labor":         ("Concrete — pour + finish",    "CY"),
    "excavation_labor":       ("Excavation",                  "LF"),
    "hardware_install":       ("Hardware Installation",       "pcs"),
    # Equipment
    "concrete_pump_per_cy":   ("Concrete Pump",               "CY"),
    "crane_per_sqft":         ("Crane / Lift Equipment",      "sqft"),
    "scaffold_per_sqft":      ("Scaffolding",                 "sqft"),
}

_TYPICAL_SQFT = 2000  # fallback when not extracted from plans


def _qty_from_result(result: dict) -> dict:
    """Pull the quantities we can price from the pipeline result.
    Computes quantities on-the-fly for results processed before quantities.py existed."""
    qty = result.get("quantities") or {}
    if not qty:
        try:
            from app.pipeline.quantities import estimate_quantities
            qty = estimate_quantities(result)
        except Exception:
            qty = {}
    foundation = result.get("foundation", {})
    project    = result.get("project", {})
    hw         = result.get("simpson_hardware", [])

    # ── Labor quantities ────────────────────────────────────────────────────
    studs = sum(item.get("estimated_qty", 0) for item in qty.get("wall_framing", []))

    subfloor = next((i.get("estimated_qty", 0) for i in qty.get("plywood", [])
                     if "subfloor" in i.get("description", "").lower()), 0)
    sheathing = next((i.get("estimated_qty", 0) for i in qty.get("plywood", [])
                      if "sheathing" in i.get("description", "").lower()), 0)

    tji = sum(item.get("estimated_qty", 0) for item in qty.get("floor_framing", [])
              if "tji" in item.get("size", "").lower() or "i-joist" in item.get("size", "").lower())

    concrete_cy    = foundation.get("concrete_cubic_yards") or 0
    excavation_lf  = foundation.get("total_lf") or 0

    hw_pieces = sum(
        (h.get("qty") or h.get("qty_mentioned") or 0)
        for h in hw if h.get("model")
    )

    # ── Equipment quantities (derived from project size / extracted data) ──
    sqft = project.get("total_sqft") or qty.get("total_sqft") or _TYPICAL_SQFT

    # Exterior wall area: sheathing sheets × 32 sqft/sheet, or estimate from perimeter
    if sheathing:
        wall_area = sheathing * 32
    else:
        perimeter_ft = 4 * math.sqrt(sqft) * 1.3
        wall_area = round(perimeter_ft * 9 * 0.8)  # height × openings factor

    return {
        "wall_stud_labor":        studs,
        "plywood_subfloor_labor": subfloor,
        "plywood_sheathing_labor":sheathing,
        "tji_joist_labor":        tji,
        "concrete_labor":         concrete_cy,
        "excavation_labor":       excavation_lf,
        "hardware_install":       hw_pieces,
        # Equipment
        "concrete_pump_per_cy":   concrete_cy,
        "crane_per_sqft":         sqft,
        "scaffold_per_sqft":      wall_area,
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
        qty  = quantities.get(key, 0)
        if rate and qty:
            line_items.append({
                "description": label,
                "qty":         round(qty, 1) if isinstance(qty, float) else qty,
                "unit":        unit,
                "rate":        rate,
                "cost":        round(rate * qty, 2),
            })

    if not line_items:
        return {}

    # Group into sections for the UI
    labor_keys = {"wall_stud_labor", "plywood_subfloor_labor", "plywood_sheathing_labor",
                  "tji_joist_labor", "concrete_labor", "excavation_labor", "hardware_install"}
    labor_items = [i for i in line_items if _key_for(i["description"]) in labor_keys]
    equip_items = [i for i in line_items if _key_for(i["description"]) not in labor_keys]

    return {
        "estimated":    True,
        "note":         "Preliminary estimate — verify all quantities before quoting",
        "line_items":   line_items,
        "labor_items":  labor_items,
        "equip_items":  equip_items,
        "labor_total":  round(sum(i["cost"] for i in labor_items), 2),
        "equip_total":  round(sum(i["cost"] for i in equip_items), 2),
        "total":        round(sum(i["cost"] for i in line_items), 2),
    }


def _key_for(description: str) -> str:
    """Reverse-map description back to rate key for grouping."""
    for key, (label, _) in _RATE_LABELS.items():
        if label == description:
            return key
    return ""
