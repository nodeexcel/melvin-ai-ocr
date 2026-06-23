import os
import re
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRAND_YELLOW = colors.HexColor("#F5C518")
BRAND_BLACK = colors.HexColor("#1A1A1A")
BRAND_GRAY = colors.HexColor("#333333")
BRAND_LIGHT = colors.HexColor("#F9F9F9")

COMPANY_NAME = "Mel's Builders Pro Systems"
TAGLINE = "On Time, On Budget, Beyond Expectations."


def _styles():
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16, textColor=BRAND_YELLOW),
        "tagline": ParagraphStyle("tagline", fontName="Helvetica-Oblique", fontSize=10, textColor=colors.white),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=13, textColor=BRAND_YELLOW, spaceBefore=16),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, textColor=colors.black),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=9, textColor=BRAND_GRAY),
    }


def _header_block(styles, project: dict) -> list:
    elements = []
    header_data = [[
        Paragraph(COMPANY_NAME, styles["title"]),
        Paragraph(TAGLINE, styles["tagline"]),
    ]]
    header_table = Table(header_data, colWidths=[4 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_BLACK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2 * inch))

    proj_rows = [
        ["Project:", project.get("name", "—")],
        ["Address:", project.get("address", "—")],
        ["Architect:", project.get("architect", "—")],
        ["Structural Engineer:", project.get("structural_engineer", "—")],
        ["Total Area:", f"{project.get('total_sqft', 0):,} sqft" if project.get("total_sqft") else "—"],
    ]
    proj_table = Table(proj_rows, colWidths=[1.8 * inch, 5.7 * inch])
    proj_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(proj_table)
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_YELLOW, spaceAfter=6))
    return elements


_HW_PHASE_MAP = {
    # Foundation: hold-downs, anchor rods
    "foundation":    ("HDU", "PHD", "HDUE", "SSTB", "SB1", "CNW"),
    # Wall: straps
    "wall_framing":  ("CMST", "MSTC", "MST", "CS14", "CS16", "ST62", "LSTA"),
    # Roof: hurricane ties
    "roof_framing":  ("HGA", "H2.5", "H10"),
    # Floor: joist hangers, beam connectors
    "floor_framing": ("LUS", "ITS", "HUS", "HUC", "HUCQ", "HHUS", "HGUS"),
}
_HW_EXACT_PHASE = {"H1": "roof_framing", "H2": "roof_framing", "H2.5A": "roof_framing",
                   "H10": "roof_framing", "H2.5": "roof_framing"}


def _hw_phase(model: str) -> str:
    m = model.upper()
    if m in _HW_EXACT_PHASE:
        return _HW_EXACT_PHASE[m]
    if m.startswith("HDU") or m.startswith("PHD") or m.startswith("SSTB"):
        return "foundation"
    for phase, prefixes in _HW_PHASE_MAP.items():
        if any(m.startswith(p.upper()) for p in prefixes):
            return phase
    return "general"


def _redistribute_phases(hw_by_phase: dict) -> dict:
    """Re-apply phase assignment at render time so cached results are also correct."""
    out: dict[str, list] = {k: [] for k in hw_by_phase}
    for phase, items in hw_by_phase.items():
        for item in items:
            model = _normalise_hw(item.get("model", ""))
            if not model:
                continue
            correct = _hw_phase(model)
            if correct not in out:
                out[correct] = []
            out[correct].append(item)
    return out


def _normalise_hw(m: str) -> str:
    for prefix in ("Simpson Strong-Tie ", "Simpson Strong Tie ", "Simpson ", "SIMPSON "):
        if m.upper().startswith(prefix.upper()):
            return m[len(prefix):].strip()
    return m.strip()


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_GRAY)
    canvas.drawString(0.75 * inch, 0.45 * inch, COMPANY_NAME)
    canvas.drawCentredString(4.25 * inch, 0.45 * inch, f"Generated: {date.today().strftime('%B %d, %Y')}")
    canvas.drawRightString(7.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(BRAND_YELLOW)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.6 * inch, 7.75 * inch, 0.6 * inch)
    canvas.restoreState()


def _section_title(text: str, styles) -> list:
    return [Paragraph(text, styles["section"]), HRFlowable(width="100%", thickness=1, color=BRAND_YELLOW, spaceAfter=4)]


def _hardware_table(hardware: list) -> Table | None:
    if not hardware:
        return None
    # Deduplicate by model, keeping highest qty
    # Normalise common prefixes so "Simpson H1" and "H1" merge
    def _normalise(m: str) -> str:
        for prefix in ("Simpson Strong-Tie ", "Simpson Strong Tie ", "Simpson "):
            if m.startswith(prefix):
                return m[len(prefix):]
        return m

    _GENERIC = {
        "nails", "nail", "bolts", "bolt", "screws", "screw", "welds", "weld",
        "strap", "straps", "holdown", "holdowns", "strong-tie", "hardware",
        "anchor bolts", "anchor bolt", "joist hangers", "joist hanger",
        "shear plates", "shear plate", "base plate", "post cap",
    }

    seen: dict[str, int] = {}
    for h in hardware:
        model = (h.get("model") or "").strip()
        if not model:
            continue
        model = _normalise(model)
        if model.lower() in _GENERIC:
            continue
        try:
            qty = int(h.get("qty", h.get("qty_mentioned", 0)) or 0)
        except (ValueError, TypeError):
            qty = 0
        if model not in seen or qty > seen[model]:
            seen[model] = qty
    # Filter zero-qty rows
    rows = [["Model", "Qty"]]
    for model, qty in seen.items():
        if qty > 0:
            rows.append([model, str(qty)])
    if len(rows) == 1:
        return None
    t = Table(rows, colWidths=[5.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_YELLOW),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _std_table(rows: list, col_widths: list) -> Table:
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_YELLOW),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _framing_section(title: str, items: list, headers: list, col_widths: list, row_fn, styles) -> list:
    """Render a framing quantities table (joists, beams, rafters, etc.)."""
    valid = [r for r in items if any(row_fn(r))]
    if not valid:
        return []
    elements = []
    elements.extend(_section_title(title, styles))
    rows = [headers] + [row_fn(r) for r in valid]
    elements.append(_std_table(rows, col_widths))
    elements.append(Spacer(1, 0.1 * inch))
    return elements


def generate_report(data: dict, output_path: str) -> None:
    """Generate a branded PDF report from the analysis result dict."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = _styles()
    elements = []

    elements.extend(_header_block(styles, data.get("project", {})))

    hw_count = len([h for h in data.get("simpson_hardware", []) if h.get("model") and (h.get("qty") or h.get("qty_mentioned", 0)) > 0])
    conn_count = len([c for c in data.get("framing_details", []) if c.get("description")])
    pages_analyzed = len([p for p in data.get("_pages", []) if p.get("category") not in ("skip", "unknown")])
    summary_parts = []
    if hw_count:      summary_parts.append(f"{hw_count} hardware items")
    if conn_count:    summary_parts.append(f"{conn_count} framing connections")
    if pages_analyzed: summary_parts.append(f"{pages_analyzed} pages analyzed")
    if summary_parts:
        elements.append(Paragraph("  ·  ".join(summary_parts), styles["body"]))
        elements.append(Spacer(1, 0.15 * inch))

    # ── Hardware by Construction Phase ────────────────────────────────────────
    # Also pull from simpson_hardware for items not in hardware_by_phase
    _raw_phase = data.get("hardware_by_phase", {})
    if not any(_raw_phase.values()):
        # Fallback: build from simpson_hardware using phase heuristics
        _raw_phase = {"foundation": [], "floor_framing": [], "wall_framing": [],
                      "roof_framing": [], "general": []}
        for h in data.get("simpson_hardware", []):
            if h.get("model"):
                _raw_phase["general"].append(h)
    hw_by_phase = _redistribute_phases(_raw_phase)
    _phase_labels = [
        ("foundation",    "Foundation Hardware"),
        ("floor_framing", "Floor Framing Hardware"),
        ("wall_framing",  "Wall Framing Hardware"),
        ("roof_framing",  "Roof Framing Hardware"),
        ("general",       "General / Connections Hardware"),
    ]
    _phase_headers = ParagraphStyle("ph", fontName="Helvetica-Bold", fontSize=8,
                                    textColor=BRAND_YELLOW, leading=10)
    _phase_cell = ParagraphStyle("pc", fontName="Helvetica", fontSize=8, leading=10)
    _PHASE_GENERIC = {
        "nails", "nail", "bolts", "bolt", "screws", "screw", "welds", "weld",
        "strap", "straps", "holdown", "holdowns", "strong-tie", "hardware",
        "anchor bolts", "anchor bolt", "joist hangers", "joist hanger",
        "shear plates", "shear plate", "base plate", "post cap",
        "ohagin roof vent", "ohagin", "roof vent", "sim. hanger",
        "post base", "anchor bolt", "holdown", "holdown strap",
        "hss", "weld", "strap", "joist hanger", "holdown",
        # Generic fasteners
        "pan head screw", "countersunk screw", "countersunk screws",
        # Sealants / membranes / tapes
        "epdm", "epdm seal", "neoprene", "neoprene pad", "neoprene bad",
        "vhb tape", "vhb", "sealant",
        # Incomplete prefix-only codes (Gemini drops the numeric suffix)
        # Full models like LUS26, HUCQ410, ABU66 are unaffected (not exact matches)
        "lus", "hucq", "abu", "hus", "lts", "cmst", "mstc",
        # MEP / non-structural items
        "hanger rod", "rod hanger",
        "e8005",      # obscure product/material code, not a Simpson connector
        # Drawing annotation labels confirmed by Melvin as non-Simpson (2026-06-19)
        "ab123", "eb456", "ea456", "ls456", "ab6", "sp789",
    }

    # Non-structural brand prefixes — Gemini extracts these from general notes.
    # Lowercased startswith check catches any variant the model produces.
    _NON_STRUCTURAL_BRANDS = (
        "schluter",   # tile edge trim system
        "pemko",      # door hardware
        "astm no",    # material standard designations
        "grace ",     # waterproofing membranes
        "allweather", # sealant brand
        "panda ",     # insulation brand
        "contega",    # building wrap
        "intello",    # air barrier membrane
        "western ",   # generic brand
        "hook #",     # door/window hardware
        "bronze ",    # architectural hardware
        "sim. ",      # drawing annotation "Similar to X" — not a model
        "sim.",       # same without space
        "jh",         # JH1/JH2 = Joist Hanger abbreviation, not a Simpson model
        "redguard",   # waterproofing membrane brand
        "nds ",       # NDS = drainage/irrigation brand (storm drains, cleanouts)
        "zoeller",    # Zoeller = sump pump brand
        "bilco",      # BILCO = access hatch / roof hatch manufacturer
        "maxeon",     # Maxeon = solar panel brand
        "sol-ark",    # Sol-Ark = solar inverter brand
        "discover ",  # Discover Helios = battery storage brand
    )

    # Substrings that disqualify any model regardless of prefix/suffix.
    _GENERIC_SUBSTRINGS = (
        "aluminum angle", "aluminum channel", "steel angle", "steel channel",
        "hss",      # HSS1/HSS 4x4 = Hollow Structural Section (steel tube)
        "bolt",     # "1/2\" DIA. BOLTS", "ANCHOR BOLTS" — generic fasteners
        "dia.",     # dimension descriptions: "1/2\" DIA."
        "glazing",   # glazing clips, glass rail brackets — architectural
        "stainless", # stainless steel fittings — not Simpson connectors
        "sleeve",    # pipe sleeve — structural penetration, not a connector
        "shock",     # shock box / shock absorber — seismic isolation, not Simpson
        " series",   # "HUCQ series", "H series" etc — generic incomplete models
        "screw",     # "SD81/4x3 SCREWS" etc — screw size descriptions, not models
        "pipe",      # Pipe Clamp, Pipe Support — MEP items
        "pvc",        # PVC pipe/fittings — plumbing, not structural
        "receptacle", # GFI Receptacle — electrical, not structural
    )

    _NAIL_PATTERN  = re.compile(r"^\d+d$")  # 8d, 10d, 16d, 20d, etc.
    _DIGIT_START   = re.compile(r"^\d")     # "1/2\" DIA. BOLTS" etc — no Simpson model starts with a digit
    _CATALOG_START = re.compile(r"^#")      # #1301-410, #896 etc — catalog/part numbers, not models

    def _is_real_model(m: str) -> bool:
        if not m:
            return False
        # 1-2 char codes like B1/W1/S1 are drawing labels, not hardware.
        # Exception: H-series (H1, H2) are real Simpson hurricane ties.
        if len(m) < 3 and not m.upper().startswith("H"):
            return False
        ml = m.lower()
        if ml in _PHASE_GENERIC:
            return False
        if _NAIL_PATTERN.match(ml):    # nail sizes: 10d, 16d, 8d
            return False
        if _DIGIT_START.match(ml):     # dimension specs: 1/2" DIA. BOLTS, 3-#5, etc.
            return False
        if _CATALOG_START.match(ml):   # catalog numbers: #1301-410, #896, #G13S-218
            return False
        if any(ml.startswith(b) for b in _NON_STRUCTURAL_BRANDS):
            return False
        if any(sub in ml for sub in _GENERIC_SUBSTRINGS):
            return False
        return True

    any_phase_hw = any(
        [h for h in hw_by_phase.get(k, [])
         if _is_real_model(_normalise_hw(h.get("model", ""))) and
         (h.get("qty") or h.get("qty_mentioned", 0))]
        for k, _ in _phase_labels
    )
    if any_phase_hw:
        elements.extend(_section_title("Hardware Schedule — by Phase", styles))
        elements.append(Paragraph(
            "* counts from OCR plan callouts where available, otherwise from Gemini extraction",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.05 * inch))
        for phase_key, phase_label in _phase_labels:
            items = [
                h for h in hw_by_phase.get(phase_key, [])
                if _is_real_model(_normalise_hw(h.get("model", ""))) and
                (h.get("qty") or h.get("qty_mentioned", 0))
            ]
            if not items:
                continue
            # Deduplicate
            seen: dict[str, int] = {}
            for h in items:
                m = _normalise_hw(h.get("model", ""))
                if not m:
                    continue
                qty = int(h.get("qty") or h.get("qty_mentioned", 0) or 0)
                if m not in seen or qty > seen[m]:
                    seen[m] = qty
            rows = [[Paragraph(phase_label, _phase_headers),
                     Paragraph("Qty", _phase_headers)]]
            for m, qty in sorted(seen.items()):
                if qty > 0:
                    rows.append([Paragraph(m, _phase_cell), Paragraph(str(qty), _phase_cell)])
            if len(rows) > 1:
                pt = Table(rows, colWidths=[5.5 * inch, 1.5 * inch])
                pt.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]))
                elements.append(pt)
                elements.append(Spacer(1, 0.06 * inch))
        elements.append(Spacer(1, 0.1 * inch))

    # ── Preliminary Quantities ────────────────────────────────────────────────
    qty = data.get("quantities", {})
    if not qty:
        # Compute at render time — estimate_quantities has its own 2000 sqft fallback
        try:
            from app.pipeline.quantities import estimate_quantities
            qty = estimate_quantities(data)
        except Exception:
            qty = {}
    _has_qty = bool(qty.get("floor_framing") or qty.get("wall_framing") or qty.get("plywood"))
    if _has_qty:
        elements.extend(_section_title("Preliminary Quantities *", styles))
        elements.append(Paragraph(
            f"* AI-estimated from {qty.get('total_sqft', 0):,} sqft floor area + extracted specs. "
            "Verify all quantities before ordering.",
            styles["body"]
        ))
        elements.append(Spacer(1, 0.08 * inch))

        # Framing lumber — show Base Qty + Waste% + Order Qty
        framing_rows = [["Description", "Size", "Base Qty", "+Waste", "Order Qty"]]
        for item in qty.get("floor_framing", []):
            base = item.get("base_qty", item.get("estimated_qty", 0))
            wpct = item.get("waste_pct")
            framing_rows.append([
                "Floor Joists",
                item.get("size", ""),
                str(base),
                f"+{wpct}%" if wpct else "—",
                str(item.get("estimated_qty", 0)),
            ])
        for item in qty.get("wall_framing", []):
            base = item.get("base_qty", item.get("estimated_qty", 0))
            wpct = item.get("waste_pct")
            length = item.get("stud_length_ft", "")
            size = item.get("size", "")
            # Size + length up front (per Melvin): e.g. "2x6 x10ft"
            size_len = f"{size} x{length}ft" if (size and length) else size
            framing_rows.append([
                f"{item.get('wall_type', '')} Wall Studs",
                size_len,
                str(base),
                f"+{wpct}%" if wpct else "—",
                str(item.get("estimated_qty", 0)),
            ])
        # Concrete row (if available)
        conc = qty.get("concrete")
        if conc:
            framing_rows.append([
                "Concrete (foundation)",
                "CY",
                str(conc.get("base_qty", 0)),
                f"+{conc.get('waste_pct', 8)}%",
                str(conc.get("estimated_qty", 0)),
            ])
        if len(framing_rows) > 1:
            elements.append(_std_table(framing_rows,
                [2.5*inch, 1.0*inch, 1.0*inch, 0.9*inch, 1.6*inch]))
            elements.append(Spacer(1, 0.08 * inch))

        # Plywood — show Base + Waste% + Order Sheets
        ply_rows = [["Plywood / Sheathing", "Grade", "Base", "+Waste", "Order Sheets"]]
        for item in qty.get("plywood", []):
            base = item.get("base_qty", item.get("estimated_qty", 0))
            wpct = item.get("waste_pct")
            ply_rows.append([
                item.get("description", ""),
                item.get("grade", ""),
                str(base),
                f"+{wpct}%" if wpct else "—",
                str(item.get("estimated_qty", 0)),
            ])
        if len(ply_rows) > 1:
            elements.append(_std_table(ply_rows, [2.5*inch, 1.8*inch, 0.9*inch, 0.9*inch, 1.9*inch]))
            elements.append(Spacer(1, 0.1 * inch))

    # Pricing/labor intentionally excluded — this is a takeoff-only report
    # (per Melvin 2026-06-23). Cost lives in a future per-trade pricing app.

    foundation = data.get("foundation", {})
    _est = foundation.get("estimated", False)
    _has_foundation = bool(foundation.get("footing_types") or foundation.get("anchor_bolts"))
    if _has_foundation:
        elements.extend(_section_title("Foundation", styles))

        # Quantity summary (from OCR — estimated, not per-type)
        total_lf = foundation.get("total_lf") or 0
        cy = foundation.get("concrete_cubic_yards") or 0
        if total_lf or cy:
            scale = foundation.get("drawing_scale", "")
            note = f"Scale: {scale}  — " if scale else ""
            note += "* AI-estimated from drawing dimensions, verify before ordering"
            elements.append(Paragraph(note, styles["body"]))
            qty_parts = []
            if total_lf:
                qty_parts.append(f"Total footing LF: {total_lf} ft *")
            if cy:
                qty_parts.append(f"Estimated concrete: {round(cy, 1)} CY *")
            elements.append(Paragraph("  |  ".join(qty_parts), styles["label"]))
            elements.append(Spacer(1, 0.1 * inch))

        # Footing schedule — type, cross-section, reinforcement
        footing_types = foundation.get("footing_types", [])
        if footing_types:
            has_rf = any(ft.get("top_rf") or ft.get("bottom_rf") for ft in footing_types)
            if has_rf:
                hdr = ["Type", "W (in)", "D (in)", "Top R/F", "Bot R/F", "Stirrups"]
                rows = [hdr]
                for ft in footing_types:
                    rows.append([
                        ft.get("type", ""),
                        str(ft.get("width_in", 0)),
                        str(ft.get("depth_in", 0)),
                        ft.get("top_rf", "—"),
                        ft.get("bottom_rf", "—"),
                        ft.get("stirrups", "—"),
                    ])
                elements.append(_std_table(rows, [1.5*inch, 0.7*inch, 0.7*inch, 1.1*inch, 1.1*inch, 1.9*inch]))
            else:
                # Fallback: no reinforcement data, show basic dimensions
                rows = [["Type", "Width (in)", "Depth (in)"]]
                for ft in footing_types:
                    rows.append([ft.get("type", ""), str(ft.get("width_in", 0)), str(ft.get("depth_in", 0))])
                elements.append(_std_table(rows, [3.0*inch, 2.0*inch, 2.0*inch]))
            elements.append(Spacer(1, 0.1 * inch))

    anchor = foundation.get("anchor_bolts") or {}
    if anchor.get("size"):
        ab_rows = [["Size", "Spacing (in)", "Qty"], [
            anchor.get("size", "—"),
            str(anchor.get("spacing_in", 0)) if anchor.get("spacing_in") else "per plan",
            str(anchor.get("qty", 0)) if anchor.get("qty") else "per plan",
        ]]
        elements.append(Paragraph("Anchor Bolts", styles["label"]))
        elements.append(_std_table(ab_rows, [2.5 * inch, 2.5 * inch, 2.0 * inch]))
        elements.append(Spacer(1, 0.1 * inch))

    lumber_specs = data.get("lumber_specs", [])
    if lumber_specs:
        elements.extend(_section_title("Lumber Specifications", styles))
        for ls in lumber_specs:
            if isinstance(ls, str):
                elements.append(Paragraph(f"  • {ls}", styles["body"]))
                elements.append(Spacer(1, 0.03 * inch))
                continue
            lumber_type = ls.get("type", ls.get("species_grade", ls.get("species", "")))
            if lumber_type:
                elements.append(Paragraph(lumber_type, styles["label"]))
            props = ls.get("properties", [])
            if props:
                for prop in props:
                    elements.append(Paragraph(f"  • {prop}", styles["body"]))
            else:
                parts = [ls.get("size", ""), ls.get("use", ""), ls.get("notes", "")]
                line = "  —  ".join(p for p in parts if p)
                if line:
                    elements.append(Paragraph(f"  {line}", styles["body"]))
            elements.append(Spacer(1, 0.05 * inch))
        elements.append(Spacer(1, 0.05 * inch))

    concrete_specs = data.get("concrete_specs", [])
    if concrete_specs:
        elements.extend(_section_title("Concrete Specifications", styles))
        for cs in concrete_specs:
            if isinstance(cs, str):
                elements.append(Paragraph(f"  • {cs}", styles["body"]))
                elements.append(Spacer(1, 0.03 * inch))
                continue
            concrete_type = cs.get("type", cs.get("location", cs.get("use", "")))
            if concrete_type:
                elements.append(Paragraph(concrete_type, styles["label"]))
            # Nested specs list: [{f'c: ..., bar_sizes: [...]}]
            nested = cs.get("specs", [])
            if nested:
                for spec in nested:
                    fc = spec.get("f'c", spec.get("fc", spec.get("strength", "")))
                    if fc:
                        elements.append(Paragraph(f"  f'c = {fc}", styles["body"]))
            else:
                # flat schema fallback
                psi = cs.get("psi", cs.get("strength_psi", ""))
                notes = cs.get("notes", "")
                line = "  —  ".join(str(p) for p in [psi, notes] if p)
                if line:
                    elements.append(Paragraph(f"  {line}", styles["body"]))
            elements.append(Spacer(1, 0.05 * inch))
        elements.append(Spacer(1, 0.05 * inch))

    floor_framing = data.get("floor_framing", {})
    _ff_est = " *" if floor_framing.get("estimated") else ""
    # Only show rows where at least one numeric value is non-zero
    joists = [r for r in floor_framing.get("joists", []) if r.get("spacing_in") or r.get("span_ft") or r.get("linear_feet") or r.get("qty_pieces")]
    beams  = [r for r in floor_framing.get("beams",  []) if r.get("span_ft") or r.get("linear_feet") or r.get("qty_pieces")]
    elements.extend(_framing_section(
        "Floor Framing — Joists", joists,
        ["Size", "Spacing (in)", "Span (ft)", f"Linear Ft{_ff_est}", f"Qty Pieces{_ff_est}"],
        [2.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch],
        lambda r: [r.get("size",""), str(r.get("spacing_in",0)), str(r.get("span_ft",0)),
                   str(r.get("linear_feet",0)), str(r.get("qty_pieces",0))],
        styles,
    ))
    elements.extend(_framing_section(
        "Floor Framing — Beams", beams,
        ["Size", "Span (ft)", f"Linear Ft{_ff_est}", f"Qty Pieces{_ff_est}"],
        [2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch],
        lambda r: [r.get("size",""), str(r.get("span_ft",0)),
                   str(r.get("linear_feet",0)), str(r.get("qty_pieces",0))],
        styles,
    ))

    wall_framing = data.get("wall_framing", {})
    _wf_est = " *" if wall_framing.get("estimated") else ""
    ext = wall_framing.get("exterior_walls") or {}
    int_ = wall_framing.get("interior_walls") or {}
    if ext.get("stud_size") or int_.get("stud_size"):
        elements.extend(_section_title("Wall Framing", styles))
        wall_rows = [["", "Stud Size", "Spacing (in)", "Height (ft)", f"Linear Ft{_wf_est}"]]
        if ext.get("stud_size"):
            wall_rows.append(["Exterior", ext.get("stud_size",""), str(ext.get("stud_spacing_in",0)),
                               str(ext.get("height_ft",0)), str(ext.get("linear_feet",0))])
        if int_.get("stud_size"):
            wall_rows.append(["Interior", int_.get("stud_size",""), str(int_.get("stud_spacing_in",0)),
                               str(int_.get("height_ft",0)), str(int_.get("linear_feet",0))])
        elements.append(_std_table(wall_rows, [1.4*inch, 1.6*inch, 1.4*inch, 1.4*inch, 1.2*inch]))
        elements.append(Spacer(1, 0.1*inch))

    roof_framing = data.get("roof_framing", {})
    _rf_est = " *" if roof_framing.get("estimated") else ""
    rafters = [r for r in roof_framing.get("rafters", []) if r.get("spacing_in") or r.get("span_ft") or r.get("linear_feet") or r.get("qty_pieces")]
    elements.extend(_framing_section(
        "Roof Framing — Rafters", rafters,
        ["Size", "Spacing (in)", "Span (ft)", f"Linear Ft{_rf_est}", f"Qty Pieces{_rf_est}"],
        [2.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch],
        lambda r: [r.get("size",""), str(r.get("spacing_in",0)), str(r.get("span_ft",0)),
                   str(r.get("linear_feet",0)), str(r.get("qty_pieces",0))],
        styles,
    ))
    ridge = roof_framing.get("ridge_beam") or {}
    if ridge.get("size"):
        elements.extend(_section_title("Roof Framing — Ridge Beam", styles))
        elements.append(Paragraph(
            f"{ridge['size']}  —  {ridge.get('linear_feet', 0)} LF", styles["body"]
        ))
        elements.append(Spacer(1, 0.1*inch))

    nailing = data.get("nailing_schedule", [])
    if nailing:
        elements.extend(_section_title("Nailing Schedule", styles))
        for n in nailing:
            if isinstance(n, str):
                elements.append(Paragraph(f"  • {n}", styles["body"]))
                elements.append(Spacer(1, 0.03 * inch))
                continue
            desc = n.get("description", "")
            connection = n.get("connection", n.get("connection_type", ""))
            nail_size = n.get("nail_size", n.get("size", ""))
            spacing = n.get("spacing", n.get("pattern", ""))
            if desc and not connection:
                elements.append(Paragraph(desc, styles["body"]))
            elif connection:
                line = connection
                if nail_size:
                    line += f"  |  {nail_size}"
                if spacing:
                    line += f"  |  {spacing}"
                elements.append(Paragraph(line, styles["body"]))
            elements.append(Spacer(1, 0.03 * inch))
        elements.append(Spacer(1, 0.05 * inch))

    # Show consolidated hardware table only when phase section is absent
    # (when phase section is shown it already covers all hardware)
    hardware = data.get("simpson_hardware", [])
    ht = _hardware_table(hardware)
    if ht and not any_phase_hw:
        elements.extend(_section_title("Simpson Hardware Schedule", styles))
        elements.append(ht)
        elements.append(Spacer(1, 0.1 * inch))

    connections = [
        c for c in data.get("framing_details", [])
        if c.get("description") and (c.get("hardware") or c.get("lumber_sizes"))
    ]
    if connections:
        elements.extend(_section_title("Framing Connection Details", styles))
        cell_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=8, leading=10)
        hdr_style = ParagraphStyle("hdr", fontName="Helvetica-Bold", fontSize=8, textColor=BRAND_YELLOW, leading=10)
        conn_rows = [[
            Paragraph("Connection Description", hdr_style),
            Paragraph("Hardware", hdr_style),
            Paragraph("Lumber Sizes", hdr_style),
        ]]
        for c in connections:
            conn_rows.append([
                Paragraph(c.get("description", ""), cell_style),
                Paragraph(c.get("hardware", ""), cell_style),
                Paragraph(", ".join(c.get("lumber_sizes", [])), cell_style),
            ])
        ct = Table(conn_rows, colWidths=[3.5 * inch, 2.0 * inch, 1.5 * inch])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(ct)
        elements.append(Spacer(1, 0.1 * inch))

    # Sheet list intentionally excluded from PDF — too long for print, available in web results view

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
