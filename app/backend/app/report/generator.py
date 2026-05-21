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
    rows = [["Model", "Qty"]]
    for h in hardware:
        if h.get("model"):
            rows.append([h.get("model", ""), str(h.get("qty", h.get("qty_mentioned", "—")))])
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

    elements.extend(_section_title("Foundation", styles))
    foundation = data.get("foundation", {})
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
        rt = Table(rebar_rows, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
        rt.setStyle(TableStyle([
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
        elements.append(Paragraph("Rebar", styles["label"]))
        elements.append(rt)
        elements.append(Spacer(1, 0.1 * inch))

    hardware = data.get("simpson_hardware", [])
    if hardware:
        elements.extend(_section_title("Simpson Hardware Schedule", styles))
        ht = _hardware_table(hardware)
        if ht:
            elements.append(ht)
            elements.append(Spacer(1, 0.1 * inch))

    connections = [c for c in data.get("framing_details", []) if c.get("description")]
    if connections:
        elements.extend(_section_title("Framing Connection Details", styles))
        conn_rows = [["Connection Description", "Hardware", "Lumber Sizes"]]
        for c in connections[:50]:
            conn_rows.append([
                c.get("description", ""),
                c.get("hardware", ""),
                ", ".join(c.get("lumber_sizes", [])),
            ])
        ct = Table(conn_rows, colWidths=[3 * inch, 1.5 * inch, 2 * inch])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLACK),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_YELLOW),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]))
        elements.append(ct)

    doc.build(elements)
