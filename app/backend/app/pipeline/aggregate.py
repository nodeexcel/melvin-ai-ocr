def aggregate_results(extractions: list[dict]) -> dict:
    result = {
        "project": {
            "name": "", "address": "", "architect": "",
            "structural_engineer": "", "total_sqft": 0, "sheet_list": [],
        },
        "foundation": {
            "footing_types": [], "concrete_cubic_yards": 0,
            "rebar": [], "anchor_bolts": {}, "hold_downs": [],
        },
        "floor_framing":   {"joists": [], "beams": [], "posts": [], "blocking": {}, "hardware": []},
        "wall_framing":    {"exterior_walls": {}, "interior_walls": {}, "headers": [], "sheathing": {}, "hardware": []},
        "roof_framing":    {"rafters": [], "ridge_beam": {}, "hip_valley": [], "sheathing": {}, "hardware": []},
        "framing_details": [],
        "simpson_hardware": [],
        "waste_factors":   {},
        "notes":           [],
        "_pages":          extractions,
    }

    for item in extractions:
        cat  = item["category"]
        data = item["data"]
        if not isinstance(data, dict):
            continue

        if cat == "schedules":
            proj = result["project"]
            if data.get("project_name") and not proj["name"]:
                proj["name"] = data["project_name"]
            if data.get("project_address") and not proj["address"]:
                proj["address"] = data["project_address"]
            if data.get("architect") and not proj["architect"]:
                proj["architect"] = data["architect"]
            if data.get("structural_engineer") and not proj["structural_engineer"]:
                proj["structural_engineer"] = data["structural_engineer"]
            if data.get("total_sqft", 0) > proj["total_sqft"]:
                proj["total_sqft"] = data["total_sqft"]
            new_sheets = data.get("sheet_list") or []
            if len(new_sheets) > len(proj["sheet_list"]):
                proj["sheet_list"] = new_sheets
            if data.get("waste_factors"):
                result["waste_factors"] = data["waste_factors"]

        elif cat == "foundation":
            result["foundation"]["footing_types"].extend(data.get("footing_types") or [])
            result["foundation"]["concrete_cubic_yards"] += data.get("concrete_cubic_yards") or 0
            result["foundation"]["rebar"].extend(data.get("rebar") or [])
            result["foundation"]["hold_downs"].extend(data.get("hold_downs") or [])
            if data.get("anchor_bolts"):
                result["foundation"]["anchor_bolts"] = data["anchor_bolts"]

        elif cat == "floor_framing":
            result["floor_framing"]["joists"].extend(data.get("joists") or [])
            result["floor_framing"]["beams"].extend(data.get("beams") or [])
            result["floor_framing"]["hardware"].extend(data.get("hardware") or [])

        elif cat == "wall_framing":
            if not result["wall_framing"]["exterior_walls"] and data.get("exterior_walls"):
                result["wall_framing"]["exterior_walls"] = data["exterior_walls"]
            result["wall_framing"]["headers"].extend(data.get("headers") or [])
            result["wall_framing"]["hardware"].extend(data.get("hardware") or [])

        elif cat == "roof_framing":
            result["roof_framing"]["rafters"].extend(data.get("rafters") or [])
            if not result["roof_framing"]["ridge_beam"] and data.get("ridge_beam"):
                result["roof_framing"]["ridge_beam"] = data["ridge_beam"]
            result["roof_framing"]["hip_valley"].extend(data.get("hip_valley") or [])
            result["roof_framing"]["hardware"].extend(data.get("hardware") or [])

        elif cat == "framing_details":
            result["framing_details"].extend(data.get("connections") or [])
            result["framing_details"].extend(data.get("hardware") or [])

    result["simpson_hardware"] = (
        result["foundation"].get("hold_downs", [])
        + result["floor_framing"].get("hardware", [])
        + result["wall_framing"].get("hardware", [])
        + result["roof_framing"].get("hardware", [])
        + [item for item in result["framing_details"] if "model" in item]
    )

    return result
