from app.report.generator import generate_report


def test_generate_report_creates_pdf(tmp_path):
    sample_data = {
        "project": {
            "name": "Test Residence",
            "address": "123 Main St, Los Angeles, CA",
            "architect": "Arch Co",
            "structural_engineer": "SE Inc",
            "total_sqft": 3500,
            "sheet_list": [{"sheet_no": "S0.1", "title": "General Notes"}],
        },
        "foundation": {
            "footing_types": [{"type": "Continuous", "width_in": 24, "depth_in": 12, "linear_feet": 120}],
            "concrete_cubic_yards": 15,
            "rebar": [{"size": "#4", "spacing_in": 12, "linear_feet": 480, "qty_pieces": 0}],
            "anchor_bolts": {"size": "5/8\"", "spacing_in": 48, "qty": 30},
            "hold_downs": [{"model": "HDU5", "qty": 4}],
        },
        "simpson_hardware": [
            {"model": "HDU5", "qty": 4},
            {"model": "LUS26", "qty": 12},
        ],
        "framing_details": [
            {"description": "beam to post connection", "hardware": "LCE4", "lumber_sizes": ["4x6"]},
        ],
        "wall_framing": {"exterior_walls": {}, "interior_walls": {}, "headers": [], "sheathing": {}, "hardware": []},
        "floor_framing": {"joists": [], "beams": [], "posts": [], "blocking": {}, "hardware": []},
        "roof_framing": {"rafters": [], "ridge_beam": {}, "hip_valley": [], "sheathing": {}, "hardware": []},
        "waste_factors": {},
        "notes": [],
    }

    output_path = tmp_path / "report.pdf"
    generate_report(sample_data, str(output_path))

    assert output_path.exists()
    assert output_path.stat().st_size > 1000
    content = output_path.read_bytes()
    assert content[:4] == b"%PDF"
