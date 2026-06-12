SYSTEM_PROMPT = (
    "You are a technical document parser for construction drawings. "
    "Extract structured data exactly as shown in the document. "
    "Return valid JSON only — no markdown fences, no explanation, no refusals."
)

_REFUSAL_PHRASES = (
    "i'm unable", "i am unable", "i cannot", "i can't", "unable to extract",
    "unable to provide", "unable to read", "not able to", "can't extract",
    "cannot extract", "cannot read", "cannot provide", "i don't see",
    "i do not see", "no text", "no data", "cannot assist",
)


def is_refusal(content: str) -> bool:
    lower = content.lower()
    return any(p in lower for p in _REFUSAL_PHRASES)


RETRY_PROMPTS: dict[str, str] = {
    "foundation": """Structural drawing. List footing types with dimensions and rebar, hold-down models, anchor bolts visible. Return JSON:
{"footing_types": [{"type": "", "width_in": 0, "depth_in": 0, "top_rf": "", "bottom_rf": "", "stirrups": "", "linear_feet": 0}], "hold_downs": [{"model": "", "qty": 0}], "anchor_bolts": {"size": "", "spacing_in": 0, "qty": 0}, "concrete_cubic_yards": 0, "notes": []}""",

    "floor_framing": """Structural drawing. List any joist sizes, beam sizes, hardware model numbers visible as annotations. Return JSON:
{"joists": [{"size": "", "spacing_in": 0, "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}], "beams": [{"size": "", "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}], "posts": [{"size": "", "height_ft": 0, "qty": 0}], "blocking": {"size": "", "linear_feet": 0}, "hardware": [{"model": "", "qty": 0}], "notes": []}""",

    "wall_framing": """Structural drawing. List any stud sizes, sheathing specs, hardware model numbers visible as annotations. Return JSON:
{"exterior_walls": {"linear_feet": 0, "stud_size": "", "stud_spacing_in": 0, "height_ft": 0}, "interior_walls": {"linear_feet": 0, "stud_size": "", "stud_spacing_in": 0, "height_ft": 0}, "headers": [{"size": "", "span_ft": 0, "qty": 0}], "sheathing": {"type": "", "thickness": "", "sheets_4x8": 0}, "hardware": [{"model": "", "qty": 0}], "notes": []}""",

    "roof_framing": """Structural drawing. List any rafter sizes, ridge beam size, hardware model numbers visible as annotations. Return JSON:
{"rafters": [{"size": "", "spacing_in": 0, "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}], "ridge_beam": {"size": "", "linear_feet": 0}, "hip_valley": [{"type": "", "size": "", "linear_feet": 0}], "blocking": {"size": "", "linear_feet": 0}, "sheathing": {"type": "", "thickness": "", "sheets_4x8": 0}, "hardware": [{"model": "", "qty": 0}], "notes": []}""",

    "framing_details": """Structural detail sheet. List any connection descriptions and Simpson hardware model numbers visible. Return JSON:
{"connections": [{"description": "", "hardware": "", "lumber_sizes": []}], "hardware": [{"model": "", "description": "", "qty_mentioned": 0}], "special_conditions": [], "notes": []}""",

    "schedules": """Document with schedules or notes. Extract any project name, address, sheet list, lumber specs, concrete specs, nailing schedule visible. Return JSON:
{"project_name": "", "project_address": "", "architect": "", "structural_engineer": "", "total_sqft": 0, "sheet_list": [{"sheet_no": "", "title": ""}], "waste_factors": {}, "lumber_specs": [], "concrete_specs": [], "nailing_schedule": [], "notes": []}""",
}


DIMENSION_PROMPTS: dict[str, str] = {
    "foundation": """Foundation plan drawing. Read dimension annotations and scale callout. Return JSON only:
{"drawing_scale": "", "footing_runs": [{"label": "", "length_ft": 0}], "total_linear_feet": 0, "concrete_cubic_yards": 0, "estimated": true}
If total_linear_feet cannot be read, return 0. Do not refuse — return zeros for unreadable fields.""",

    "floor_framing": """Floor framing plan drawing. Read span dimensions, spacing callouts, scale callout. Return JSON only:
{"drawing_scale": "", "joist_span_ft": 0, "joist_spacing_in": 0, "floor_width_ft": 0, "total_joist_lf": 0, "beam_spans": [{"label": "", "length_ft": 0}], "estimated": true}
If dimensions cannot be read, return 0. Do not refuse — return zeros for unreadable fields.""",

    "wall_framing": """Floor plan or shear wall plan drawing. Read perimeter wall dimensions and scale callout. Return JSON only:
{"drawing_scale": "", "exterior_lf": 0, "interior_lf": 0, "estimated": true}
If dimensions cannot be read, return 0. Do not refuse — return zeros for unreadable fields.""",

    "roof_framing": """Roof framing plan drawing. Read rafter spans, spacing callouts, ridge beam length, scale callout. Return JSON only:
{"drawing_scale": "", "rafter_span_ft": 0, "rafter_spacing_in": 0, "roof_width_ft": 0, "total_rafter_lf": 0, "ridge_lf": 0, "estimated": true}
If dimensions cannot be read, return 0. Do not refuse — return zeros for unreadable fields.""",
}


EXTRACTION_PROMPTS: dict[str, str] = {
    "foundation": """This is a foundation plan or footing detail sheet. Look for a GRADE BEAM SCHEDULE or FOOTING SCHEDULE table on the sheet.

Extract ALL of the following as JSON:
{
  "footing_types": [
    {
      "type": "",
      "width_in": 0,
      "depth_in": 0,
      "top_rf": "",
      "bottom_rf": "",
      "stirrups": "",
      "linear_feet": 0
    }
  ],
  "concrete_cubic_yards": 0,
  "anchor_bolts": {"size": "", "spacing_in": 0, "qty": 0},
  "hold_downs": [{"model": "", "qty": 0}],
  "notes": []
}

For top_rf and bottom_rf: extract the reinforcement string exactly as shown (e.g. "3-#5", "5-#7").
For stirrups: extract spacing (e.g. "#4 @12\" O.C.").
If no schedule table is visible, extract what you can from callouts.""",

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
