import os

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
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=22, textColor=BRAND_YELLOW),
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

    seen: dict[str, int] = {}
    for h in hardware:
        model = (h.get("model") or "").strip()
        if not model:
            continue
        model = _normalise(model)
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
    t = Table(rows, colWidths=[2.5 * inch, 1 * inch])
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

    foundation = data.get("foundation", {})
    _has_foundation = bool(foundation.get("footing_types") or foundation.get("rebar"))
    if _has_foundation:
        elements.extend(_section_title("Foundation", styles))
    footing_rows = [["Type", "Width (in)", "Depth (in)", "Linear Ft"]]
    for ft in foundation.get("footing_types", []):
        footing_rows.append([
            ft.get("type", ""), str(ft.get("width_in", 0)),
            str(ft.get("depth_in", 0)), str(ft.get("linear_feet", 0)),
        ])
    if len(footing_rows) > 1:
        t = Table(footing_rows, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
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
        elements.append(t)
        elements.append(Spacer(1, 0.1 * inch))

    rebar = foundation.get("rebar", [])
    if rebar:
        rebar_rows = [["Size", "Spacing (in)", "Linear Ft", "Qty Pieces"]]
        for r in rebar:
            rebar_rows.append([
                r.get("size", ""), str(r.get("spacing_in", 0)),
                str(r.get("linear_feet", 0)), str(r.get("qty_pieces", 0)),
            ])
        elements.append(Paragraph("Rebar", styles["label"]))
        elements.append(_std_table(rebar_rows, [1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch]))
        elements.append(Spacer(1, 0.1 * inch))

    anchor = foundation.get("anchor_bolts") or {}
    if anchor.get("size"):
        ab_rows = [["Size", "Spacing (in)", "Qty"], [
            anchor.get("size", "—"),
            str(anchor.get("spacing_in", 0)) if anchor.get("spacing_in") else "per plan",
            str(anchor.get("qty", 0)) if anchor.get("qty") else "per plan",
        ]]
        elements.append(Paragraph("Anchor Bolts", styles["label"]))
        elements.append(_std_table(ab_rows, [2 * inch, 2 * inch, 1.5 * inch]))
        elements.append(Spacer(1, 0.1 * inch))

    cy = foundation.get("concrete_cubic_yards") or 0
    if cy:
        elements.append(Paragraph(f"Estimated Concrete: {cy} CY", styles["body"]))
        elements.append(Spacer(1, 0.05 * inch))

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
    elements.extend(_framing_section(
        "Floor Framing — Joists",
        floor_framing.get("joists", []),
        ["Size", "Spacing (in)", "Span (ft)", "Linear Ft", "Qty Pieces"],
        [1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch],
        lambda r: [r.get("size",""), str(r.get("spacing_in",0)), str(r.get("span_ft",0)),
                   str(r.get("linear_feet",0)), str(r.get("qty_pieces",0))],
        styles,
    ))
    elements.extend(_framing_section(
        "Floor Framing — Beams",
        floor_framing.get("beams", []),
        ["Size", "Span (ft)", "Linear Ft", "Qty Pieces"],
        [2*inch, 1.5*inch, 1.5*inch, 1.5*inch],
        lambda r: [r.get("size",""), str(r.get("span_ft",0)),
                   str(r.get("linear_feet",0)), str(r.get("qty_pieces",0))],
        styles,
    ))

    wall_framing = data.get("wall_framing", {})
    ext = wall_framing.get("exterior_walls") or {}
    int_ = wall_framing.get("interior_walls") or {}
    if ext.get("stud_size") or int_.get("stud_size"):
        elements.extend(_section_title("Wall Framing", styles))
        wall_rows = [["", "Stud Size", "Spacing (in)", "Height (ft)", "Linear Ft"]]
        if ext.get("stud_size"):
            wall_rows.append(["Exterior", ext.get("stud_size",""), str(ext.get("stud_spacing_in",0)),
                               str(ext.get("height_ft",0)), str(ext.get("linear_feet",0))])
        if int_.get("stud_size"):
            wall_rows.append(["Interior", int_.get("stud_size",""), str(int_.get("stud_spacing_in",0)),
                               str(int_.get("height_ft",0)), str(int_.get("linear_feet",0))])
        elements.append(_std_table(wall_rows, [1.2*inch, 1.5*inch, 1.3*inch, 1.3*inch, 1.2*inch]))
        elements.append(Spacer(1, 0.1*inch))

    roof_framing = data.get("roof_framing", {})
    elements.extend(_framing_section(
        "Roof Framing — Rafters",
        roof_framing.get("rafters", []),
        ["Size", "Spacing (in)", "Span (ft)", "Linear Ft", "Qty Pieces"],
        [1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch],
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

    hardware = data.get("simpson_hardware", [])
    ht = _hardware_table(hardware)
    if ht:
        elements.extend(_section_title("Simpson Hardware Schedule", styles))
        elements.append(ht)
        elements.append(Spacer(1, 0.1 * inch))

    connections = [c for c in data.get("framing_details", []) if c.get("description")]
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
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(ct)
        elements.append(Spacer(1, 0.1 * inch))

    sheet_list = data.get("project", {}).get("sheet_list", [])
    if sheet_list:
        elements.extend(_section_title("Sheet List", styles))
        sheet_rows = [["Sheet No.", "Title"]]
        for s in sheet_list:
            if isinstance(s, dict):
                sheet_rows.append([s.get("sheet_no", s.get("number", "")), s.get("title", "")])
            else:
                sheet_rows.append([str(s), ""])
        st = Table(sheet_rows, colWidths=[1.5 * inch, 6 * inch])
        st.setStyle(TableStyle([
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
        elements.append(st)

    doc.build(elements)
