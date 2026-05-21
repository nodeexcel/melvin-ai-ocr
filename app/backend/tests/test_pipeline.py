from app.pipeline.classify import classify_page, extract_sheet_info
from app.pipeline.aggregate import aggregate_results


def test_extract_sheet_info_pattern1():
    text = "GENERAL NOTES\r\nS0.1\r\nSome other text"
    sheet_no, title = extract_sheet_info(text)
    assert sheet_no == "S0.1"
    assert "general" in title.lower()


def test_extract_sheet_info_pattern5_av_job():
    text = "AV JOB:\r\nFOUNDATION AND\r\nBASEMENT PLANS\r\nS-2.1\r\nAshley Vance"
    sheet_no, title = extract_sheet_info(text)
    assert sheet_no == "S-2.1"
    assert "foundation" in title.lower()


def test_classify_schedules():
    text = "STRUCTURAL NOTES\r\nS0.1\r\n"
    assert classify_page(text) == "schedules"


def test_classify_skip():
    text = "LIGHTING PLAN\r\nE1.0\r\n"
    assert classify_page(text) == "skip"


def test_classify_unknown():
    assert classify_page("no title block here") == "unknown"


def test_aggregate_results_merges_project_info():
    extractions = [
        {
            "page": 1,
            "category": "schedules",
            "method": "text",
            "data": {
                "project_name": "Test Project",
                "project_address": "123 Main St",
                "architect": "Arch Co",
                "structural_engineer": "SE Inc",
                "total_sqft": 5000,
                "sheet_list": [{"sheet_no": "S0.1", "title": "General Notes"}],
                "lumber_specs": [],
                "concrete_specs": [],
                "nailing_schedule": [],
                "waste_factors": {},
            },
        }
    ]
    result = aggregate_results(extractions)
    assert result["project"]["name"] == "Test Project"
    assert result["project"]["structural_engineer"] == "SE Inc"
    assert len(result["project"]["sheet_list"]) == 1


def test_aggregate_results_merges_hardware():
    extractions = [
        {
            "page": 2,
            "category": "framing_details",
            "method": "text",
            "data": {
                "connections": [{"description": "beam to post", "hardware": "LCE4", "lumber_sizes": ["4x4"]}],
                "hardware": [{"model": "LCE4", "description": "column cap", "qty_mentioned": 4}],
                "special_conditions": [],
                "notes": [],
            },
        }
    ]
    result = aggregate_results(extractions)
    assert any(h.get("model") == "LCE4" for h in result["simpson_hardware"])
