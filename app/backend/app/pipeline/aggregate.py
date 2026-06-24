from collections import Counter

from app.pipeline.hardware import clean_result_hardware


def _most_common(values: list[str]) -> str:
    """Return the most frequently occurring non-empty string in values."""
    counts = Counter(v.strip() for v in values if v and v.strip())
    return counts.most_common(1)[0][0] if counts else ""


def _resolve_project_field(records: list[dict], field: str) -> str:
    """Most-common value for a project field, preferring records that also carry a
    structural_engineer (true structural title-block pages). Early pages (vicinity
    maps, adjacent-property notes, civil sheets) often list a different address but
    no SE, and would otherwise win on raw frequency. Falls back to all records."""
    title_block = [r for r in records if r.get("structural_engineer")]
    pool = title_block if any(r.get(field) for r in title_block) else records
    return _most_common([r.get(field, "") for r in pool])


def aggregate_results(extractions: list[dict]) -> dict:
    result = {
        "project": {
            "name": "", "address": "", "architect": "",
            "structural_engineer": "", "total_sqft": 0, "sheet_list": [],
        },
        "foundation": {
            "footing_types": [], "concrete_cubic_yards": 0,
            "total_lf": 0,
            "anchor_bolts": {}, "hold_downs": [],
            "drawing_scale": "", "estimated": False,
        },
        "floor_framing":   {"joists": [], "beams": [], "posts": [], "blocking": {}, "hardware": [], "drawing_scale": "", "estimated": False},
        "wall_framing":    {"exterior_walls": {}, "interior_walls": {}, "headers": [], "sheathing": {}, "hardware": [], "drawing_scale": "", "estimated": False},
        "roof_framing":    {"rafters": [], "ridge_beam": {}, "hip_valley": [], "sheathing": {}, "hardware": [], "drawing_scale": "", "estimated": False},
        "framing_details": [],
        "simpson_hardware": [],
        "lumber_specs":    [],
        "concrete_specs":  [],
        "nailing_schedule": [],
        "waste_factors":   {},
        "notes":           [],
        "_pages":          extractions,
    }

    # Collect all candidate values for project string fields across pages.
    # Use most-common instead of first-non-empty to avoid early pages with
    # wrong addresses (adjacent properties, vicinity maps) winning.
    proj_records: list[dict] = []

    for item in extractions:
        cat  = item["category"]
        data = item["data"]
        if not isinstance(data, dict):
            continue

        if cat == "schedules":
            rec = {"name": (data.get("project_name") or "").strip(),
                   "address": (data.get("project_address") or "").strip(),
                   "architect": (data.get("architect") or "").strip(),
                   "structural_engineer": (data.get("structural_engineer") or "").strip()}
            if any(rec.values()):
                proj_records.append(rec)
            if data.get("total_sqft", 0) > result["project"]["total_sqft"]:
                result["project"]["total_sqft"] = data["total_sqft"]
            new_sheets = data.get("sheet_list") or []
            if len(new_sheets) > len(result["project"]["sheet_list"]):
                result["project"]["sheet_list"] = new_sheets
            if data.get("waste_factors"):
                result["waste_factors"] = data["waste_factors"]
            result["lumber_specs"].extend(data.get("lumber_specs") or [])
            result["concrete_specs"].extend(data.get("concrete_specs") or [])
            result["nailing_schedule"].extend(data.get("nailing_schedule") or [])

        elif cat == "foundation":
            result["foundation"]["footing_types"].extend(data.get("footing_types") or [])
            _cy = data.get("concrete_cubic_yards") or 0
            if isinstance(_cy, (int, float)):
                result["foundation"]["concrete_cubic_yards"] += _cy
            result["foundation"]["hold_downs"].extend(data.get("hold_downs") or [])
            if data.get("anchor_bolts"):
                result["foundation"]["anchor_bolts"] = data["anchor_bolts"]
            if data.get("estimated"):
                result["foundation"]["estimated"] = True
            if data.get("drawing_scale") and not result["foundation"]["drawing_scale"]:
                result["foundation"]["drawing_scale"] = data["drawing_scale"]

        elif cat == "floor_framing":
            # Dedup joists by (size, spacing_in) — same spec appears on multiple plan pages.
            # Keep the entry with the highest qty_pieces; fall back to first seen.
            existing_joists = {
                (j.get("size", ""), j.get("spacing_in", 0)): j
                for j in result["floor_framing"]["joists"]
            }
            for joist in (data.get("joists") or []):
                key = (joist.get("size", ""), joist.get("spacing_in", 0))
                if key not in existing_joists or joist.get("qty_pieces", 0) > existing_joists[key].get("qty_pieces", 0):
                    existing_joists[key] = joist
            result["floor_framing"]["joists"] = list(existing_joists.values())
            result["floor_framing"]["beams"].extend(data.get("beams") or [])
            result["floor_framing"]["hardware"].extend(data.get("hardware") or [])
            if data.get("estimated"):
                result["floor_framing"]["estimated"] = True
            if data.get("drawing_scale") and not result["floor_framing"]["drawing_scale"]:
                result["floor_framing"]["drawing_scale"] = data["drawing_scale"]

        elif cat == "wall_framing":
            if not result["wall_framing"]["exterior_walls"] and data.get("exterior_walls"):
                result["wall_framing"]["exterior_walls"] = data["exterior_walls"]
            result["wall_framing"]["headers"].extend(data.get("headers") or [])
            result["wall_framing"]["hardware"].extend(data.get("hardware") or [])
            if data.get("estimated"):
                result["wall_framing"]["estimated"] = True
            if data.get("drawing_scale") and not result["wall_framing"]["drawing_scale"]:
                result["wall_framing"]["drawing_scale"] = data["drawing_scale"]

        elif cat == "roof_framing":
            result["roof_framing"]["rafters"].extend(data.get("rafters") or [])
            if not result["roof_framing"]["ridge_beam"] and data.get("ridge_beam"):
                result["roof_framing"]["ridge_beam"] = data["ridge_beam"]
            result["roof_framing"]["hip_valley"].extend(data.get("hip_valley") or [])
            result["roof_framing"]["hardware"].extend(data.get("hardware") or [])
            if data.get("estimated"):
                result["roof_framing"]["estimated"] = True
            if data.get("drawing_scale") and not result["roof_framing"]["drawing_scale"]:
                result["roof_framing"]["drawing_scale"] = data["drawing_scale"]

        elif cat == "framing_details":
            result["framing_details"].extend(data.get("connections") or [])
            result["framing_details"].extend(data.get("hardware") or [])

    # Resolve project string fields. Name/address prefer structural title-block
    # pages (those with an SE) to avoid early-page wrong addresses winning on
    # frequency; architect/SE use plain most-common.
    result["project"]["name"]                = _resolve_project_field(proj_records, "name")
    result["project"]["address"]             = _resolve_project_field(proj_records, "address")
    result["project"]["architect"]           = _most_common([r["architect"] for r in proj_records])
    result["project"]["structural_engineer"] = _most_common([r["structural_engineer"] for r in proj_records])

    # Flat list for backward compatibility
    result["simpson_hardware"] = (
        result["foundation"].get("hold_downs", [])
        + result["floor_framing"].get("hardware", [])
        + result["wall_framing"].get("hardware", [])
        + result["roof_framing"].get("hardware", [])
        + [item for item in result["framing_details"] if "model" in item]
    )
    result["_ocr_hardware_counts"] = {}  # populated by inject_lf_data if OCR ran

    # Phase-based hardware — organized by where items are installed
    _phase_hw: dict[str, list] = {
        "foundation":    list(result["foundation"].get("hold_downs", [])),
        "floor_framing": list(result["floor_framing"].get("hardware", [])),
        "wall_framing":  list(result["wall_framing"].get("hardware", [])),
        "roof_framing":  list(result["roof_framing"].get("hardware", [])),
        "general":       [],
    }
    # Redistribute framing_details hardware using phase heuristics
    for item in result["framing_details"]:
        if "model" not in item:
            continue
        phase = _phase_for_model(_normalise_model(item.get("model", "")))
        _phase_hw[phase].append(item)
    result["hardware_by_phase"] = _phase_hw

    # Clean stored hardware (dedup, drop noise + pure-zero-qty) so raw_json
    # matches what the report renders. Re-applied after OCR injection too.
    clean_result_hardware(result)
    return result


def _phase_for_model(model: str) -> str:
    """Assign a hardware model to a construction phase by prefix heuristics."""
    m = model.upper()
    # Foundation: hold-downs, anchor rods
    if any(m.startswith(p) for p in ("HDU", "PHD", "HDUE", "SSTB", "SB1", "CNW")):
        return "foundation"
    # Straps → wall framing (check before joist hangers to avoid false matches)
    if any(m.startswith(p) for p in ("CMST", "MSTC", "MST", "CS14", "CS16", "ST62", "LSTA")):
        return "wall_framing"
    # Hurricane ties + roof connectors → roof framing
    if any(m.startswith(p) for p in ("HGA", "H2.5", "H10", "H1 ", "H1\t")):
        return "roof_framing"
    if m in ("H1", "H2", "H2.5", "H2.5A", "H10"):
        return "roof_framing"
    # Joist hangers → floor framing
    if any(m.startswith(p) for p in ("LUS", "ITS", "HUS", "HUC", "HUCQ", "HHUS", "HGUS")):
        return "floor_framing"
    return "general"


def _normalise_model(m: str) -> str:
    for prefix in ("Simpson Strong-Tie ", "Simpson Strong Tie ", "Simpson ", "SIMPSON "):
        if m.upper().startswith(prefix.upper()):
            return m[len(prefix):].strip()
    return m.strip()


def _merge_hardware(existing: list[dict], ocr_counts: dict[str, int]) -> list[dict]:
    """
    Merge OCR-counted hardware into existing simpson_hardware list.
    OCR count takes priority when it's higher than Gemini's extracted qty.
    """
    # normalise inline (same logic as generator.py _hardware_table)
    merged = {_normalise_model(h.get("model", "")): h.copy()
              for h in existing if h.get("model")}
    for raw_model, count in ocr_counts.items():
        model = _normalise_model(raw_model)
        if model in merged:
            # Take the higher of OCR count vs Gemini qty
            existing_qty = int(merged[model].get("qty", merged[model].get("qty_mentioned", 0)) or 0)
            if count > existing_qty:
                merged[model]["qty"] = count
                merged[model]["qty_source"] = "ocr_callout"
        else:
            merged[model] = {"model": model, "qty": count, "qty_source": "ocr_callout"}
    return list(merged.values())


def inject_lf_data(result: dict, lf_data: dict) -> dict:
    """Inject PaddleOCR footing LF + derived CY into the foundation section.
    Hardware counts are handled separately by inject_hardware_counts() so they
    survive even when footing LF is 0 (the previous combined version early-returned
    on LF==0, silently dropping the dedicated hardware pass). Mutates result."""
    foundation = result.get("foundation", {})
    grand_lf = lf_data.get("grand_total_lf", 0)
    if not grand_lf:
        return result

    # Store total LF — do NOT distribute per footing type (that's fabricated data)
    foundation["total_lf"] = round(grand_lf, 1)
    foundation["estimated"] = True

    for page in lf_data.get("pages", []):
        if page.get("drawing_scale") and not foundation.get("drawing_scale"):
            foundation["drawing_scale"] = page["drawing_scale"]

    # Calculate CY from total LF × weighted average footing cross-section
    if foundation.get("concrete_cubic_yards", 0) == 0:
        footing_types = foundation.get("footing_types", [])
        dims = [
            (ft.get("width_in", 0), ft.get("depth_in", 0))
            for ft in footing_types
            if ft.get("width_in") and ft.get("depth_in")
        ]
        if dims:
            avg_w = sum(d[0] for d in dims) / len(dims)
            avg_d = sum(d[1] for d in dims) / len(dims)
            foundation["concrete_cubic_yards"] = round(grand_lf * (avg_w / 12) * (avg_d / 12) / 27, 1)

    return result


def inject_hardware_counts(result: dict, ocr_counts: dict) -> dict:
    """Merge OCR hardware callout counts into simpson_hardware + hardware_by_phase.
    Independent of footing LF — runs even when LF is 0 (foundation-only LF scope
    means the dedicated all-structural hardware pass must inject on its own).
    OCR count wins when higher than the extracted qty. Mutates result."""
    if not ocr_counts:
        return result
    result["_ocr_hardware_counts"] = {**result.get("_ocr_hardware_counts", {}), **ocr_counts}
    result["simpson_hardware"] = _merge_hardware(result.get("simpson_hardware", []), ocr_counts)
    for raw_model, count in ocr_counts.items():
        model = _normalise_model(raw_model)
        phase = _phase_for_model(model)
        phase_list = result.get("hardware_by_phase", {}).get(phase, [])
        existing = next((h for h in phase_list if _normalise_model(h.get("model", "")) == model), None)
        if existing:
            if count > int(existing.get("qty", 0) or 0):
                existing["qty"] = count
                existing["qty_source"] = "ocr_callout"
        else:
            phase_list.append({"model": model, "qty": count, "qty_source": "ocr_callout"})
    return result
