SYSTEM_PROMPT = (
    "You are a technical document parser for construction drawings. "
    "Extract structured data exactly as shown in the document. "
    "Return valid JSON only — no markdown fences, no explanation, no refusals."
)

EXTRACTION_PROMPTS: dict[str, str] = {
    "foundation": """This is a foundation plan or footing detail sheet.
Extract ALL of the following as JSON:
{
  "footing_types": [{"type": "", "width_in": 0, "depth_in": 0, "linear_feet": 0}],
  "concrete_cubic_yards": 0,
  "rebar": [{"size": "", "spacing_in": 0, "linear_feet": 0, "qty_pieces": 0}],
  "anchor_bolts": {"size": "", "spacing_in": 0, "qty": 0},
  "hold_downs": [{"model": "", "qty": 0}],
  "notes": []
}""",

    "floor_framing": """This is a floor framing plan or detail sheet.
Extract ALL of the following as JSON:
{
  "joists": [{"size": "", "spacing_in": 0, "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}],
  "beams": [{"size": "", "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}],
  "posts": [{"size": "", "height_ft": 0, "qty": 0}],
  "blocking": {"size": "", "linear_feet": 0},
  "hardware": [{"model": "", "qty": 0}],
  "notes": []
}""",

    "wall_framing": """This is a floor plan or shear wall plan.
Extract ALL of the following as JSON:
{
  "exterior_walls": {"linear_feet": 0, "stud_size": "", "stud_spacing_in": 0, "height_ft": 0},
  "interior_walls": {"linear_feet": 0, "stud_size": "", "stud_spacing_in": 0, "height_ft": 0},
  "headers": [{"size": "", "span_ft": 0, "qty": 0}],
  "sheathing": {"type": "", "thickness": "", "sheets_4x8": 0},
  "hardware": [{"model": "", "qty": 0}],
  "notes": []
}""",

    "roof_framing": """This is a roof framing plan or detail sheet.
Extract ALL of the following as JSON:
{
  "rafters": [{"size": "", "spacing_in": 0, "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}],
  "ridge_beam": {"size": "", "linear_feet": 0},
  "hip_valley": [{"type": "", "size": "", "linear_feet": 0}],
  "blocking": {"size": "", "linear_feet": 0},
  "sheathing": {"type": "", "thickness": "", "sheets_4x8": 0},
  "hardware": [{"model": "", "qty": 0}],
  "notes": []
}""",

    "framing_details": """This is a structural framing detail sheet.
Extract ALL of the following as JSON:
{
  "connections": [{"description": "", "hardware": "", "lumber_sizes": []}],
  "hardware": [{"model": "", "description": "", "qty_mentioned": 0}],
  "special_conditions": [],
  "notes": []
}""",

    "schedules": """This is a general notes, schedule, or cover sheet.
Extract ALL of the following as JSON:
{
  "project_name": "",
  "project_address": "",
  "architect": "",
  "structural_engineer": "",
  "total_sqft": 0,
  "sheet_list": [{"sheet_no": "", "title": ""}],
  "waste_factors": {},
  "lumber_specs": [],
  "concrete_specs": [],
  "nailing_schedule": [],
  "notes": []
}""",
}
