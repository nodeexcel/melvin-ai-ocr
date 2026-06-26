"""Stage 4 of the callout engine: extract hardware from resolved detail crops.

Given the resolved records from stage 3 (callout_resolve.py), this module
locates the detail box on the PDF, extracts its text (CAD text-layer path)
or renders it as an image (vision path), sends to Gemini, and returns
structured hardware with provenance.

Modality auto-detection:
  - If the crop region has ≥ MIN_TEXT_CHARS characters in the text layer
    → text path (get_text_bounded → Gemini text inference, no render cost)
  - Otherwise → vision path (render crop at ≥400 DPI → Gemini vision)

Output shape per detail:
  {
    "detail_num": str,
    "sheet_id": str,
    "callout_count": int,
    "typical": bool,
    "callout_pages": list[int],
    "per_detail_hardware": [{"model": str, "qty_per_detail": int}],
    "total_hardware": [{"model": str, "total_qty": int, "provenance": str}],
    "modality": "text_layer" | "vision" | "unresolved",
    "resolved": bool,
  }
total_qty = qty_per_detail * callout_count (or callout_count if qty_per_detail==0).
"""

from __future__ import annotations

import json
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import google.generativeai as genai
import pypdfium2 as pdfium

from app.pipeline.hardware import is_real_model, normalise_model


# ── Constants ───────────────────────────────────────────────────────────────────

MIN_TEXT_CHARS = 30       # fewer chars → assume raster, use vision path
RENDER_SCALE   = 400 / 72 # ~400 DPI for crop renders

_DETAIL_HW_PROMPT = (
    "You are reading text extracted from a single structural engineering detail box.\n"
    "List only Simpson Strong-Tie hardware model numbers visible in this text.\n"
    "Examples of valid models: HDU2, HDU5, LUS28, LUS210, MSTC28, A35, HUCQ410, PCZ, ABU66, CMST12, WSWH-18.\n"
    "Return JSON only — no prose:\n"
    '{"hardware": [{"model": "<model>", "qty_mentioned": <int or 0>}]}\n'
    "- qty_mentioned: numeric count if one is visible right next to the model name; otherwise 0.\n"
    "- Omit lumber specs (PSL, LVL, DF#2), dimension labels, drawing callout numbers, and non-Simpson brands.\n"
    "- If no Simpson hardware is present, return {\"hardware\": []}."
)

_DETAIL_HW_VISION_PROMPT = (
    "This image is a cropped structural engineering detail from a construction plan.\n"
    "List only Simpson Strong-Tie hardware model numbers you can read in the image.\n"
    "Return JSON only:\n"
    '{"hardware": [{"model": "<model>", "qty_mentioned": <int or 0>}]}\n'
    "- qty_mentioned: if a count appears next to the model (e.g. '(2)' or 'x3'), use it; otherwise 0.\n"
    "- Omit lumber specs, dimension callouts, and non-Simpson brands.\n"
    "- If no Simpson hardware is visible, return {\"hardware\": []}."
)


# ── Internal helpers ─────────────────────────────────────────────────────────────

def _parse_hw_response(content: str) -> list[dict]:
    """Parse JSON hardware list from LLM response. Returns [] on failure."""
    if not content:
        return []
    # Strip markdown fences
    if "```" in content:
        parts = content.split("```")
        content = parts[1].lstrip("json").strip() if len(parts) > 1 else content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract just the JSON object
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []

    hw = data.get("hardware", [])
    if not isinstance(hw, list):
        return []
    return hw


def _gemini_retry_delay(error: Exception) -> int:
    match = re.search(r"retry.*?(\d+)\s*seconds?", str(error), re.IGNORECASE)
    return int(match.group(1)) + 2 if match else 65


def _call_gemini_text(google_api_key: str, crop_text: str) -> list[dict]:
    """Send crop text to Gemini and return parsed hardware list."""
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    config = genai.GenerationConfig(
        temperature=0,
        max_output_tokens=2000,
        response_mime_type="application/json",
    )
    prompt = f"{_DETAIL_HW_PROMPT}\n\n<detail_text>\n{crop_text}\n</detail_text>"
    try:
        response = model.generate_content(prompt, generation_config=config)
        return _parse_hw_response(response.text or "")
    except Exception as e:
        if "429" in str(e):
            time.sleep(_gemini_retry_delay(e))
            try:
                response = model.generate_content(prompt, generation_config=config)
                return _parse_hw_response(response.text or "")
            except Exception:
                return []
        return []


def _call_gemini_vision(google_api_key: str, pil_image: Any) -> list[dict]:
    """Send a PIL crop image to Gemini vision and return parsed hardware list."""
    genai.configure(api_key=google_api_key)
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    config = genai.GenerationConfig(
        temperature=0,
        max_output_tokens=2000,
        response_mime_type="application/json",
    )
    try:
        response = model.generate_content(
            [_DETAIL_HW_VISION_PROMPT, pil_image],
            generation_config=config,
        )
        return _parse_hw_response(response.text or "")
    except Exception as e:
        if "429" in str(e):
            time.sleep(_gemini_retry_delay(e))
            try:
                response = model.generate_content(
                    [_DETAIL_HW_VISION_PROMPT, pil_image],
                    generation_config=config,
                )
                return _parse_hw_response(response.text or "")
            except Exception:
                return []
        return []


def _validate_hw(raw: list[dict]) -> list[dict]:
    """Filter and normalise the LLM hardware output.

    Applies is_real_model() + normalise_model() to each entry.
    Deduplicates (keeps highest qty_mentioned). Returns clean list.
    """
    best: dict[str, int] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        model = normalise_model(str(item.get("model", ""))).upper()
        if not is_real_model(model):
            continue
        try:
            qty = int(item.get("qty_mentioned") or 0)
        except (ValueError, TypeError):
            qty = 0
        best[model] = max(best.get(model, 0), qty)
    return [{"model": m, "qty_per_detail": q} for m, q in best.items()]


def render_crop(
    pdf_path: str | Path,
    page_index: int,
    crop_bbox: tuple[float, float, float, float],
    dpi: int = 400,
) -> Any:
    """Render a crop region of a PDF page as a PIL Image.

    crop_bbox: (x0, y0, x1, y1) in PDF points (y=0 at bottom).
    Returns a PIL Image in RGB mode.
    """
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        page = doc[page_index]
        w, h = page.get_size()
        x0, y0, x1, y1 = crop_bbox
        # pdfium crop param = amount to cut from each edge (left, bottom, right, top)
        cut = (x0, y0, w - x1, h - y1)
        cut = tuple(max(0.0, c) for c in cut)  # clamp negatives
        scale = dpi / 72.0
        bitmap = page.render(scale=scale, crop=cut)
        return bitmap.to_pil()
    finally:
        doc.close()


# ── Public API ───────────────────────────────────────────────────────────────────

def extract_detail_hardware(
    google_api_key: str,
    pdf_path: str | Path,
    resolved_records: list[dict],
) -> list[dict]:
    """Stage 4: extract Simpson hardware from each resolved detail crop.

    resolved_records: output of callout_resolve.resolve_callouts().
    Unresolved records (resolved=False) are passed through unchanged.

    Returns one record per input item with per_detail_hardware, total_hardware,
    and modality fields added.
    """
    pdf_path = Path(pdf_path)
    doc = pdfium.PdfDocument(str(pdf_path))

    try:
        results = []
        for rec in resolved_records:
            base = {
                "detail_num":   rec["detail_num"],
                "sheet_id":     rec["sheet_id"],
                "callout_count": rec["callout_count"],
                "typical":      rec["typical"],
                "callout_pages": rec.get("callout_pages", []),
                "resolved":     rec["resolved"],
            }

            if not rec["resolved"]:
                results.append({
                    **base,
                    "per_detail_hardware": [],
                    "total_hardware": [],
                    "modality": "unresolved",
                })
                continue

            page_idx   = rec["detail_page_index"]
            crop_bbox  = rec["crop_bbox"]
            callout_n  = rec["callout_count"]

            # --- Determine modality: check text layer first ---
            page     = doc[page_idx]
            textpage = page.get_textpage()
            x0, y0, x1, y1 = crop_bbox
            crop_text = textpage.get_text_bounded(left=x0, bottom=y0, right=x1, top=y1)
            crop_text = crop_text.strip()

            if len(crop_text) >= MIN_TEXT_CHARS:
                modality = "text_layer"
                raw_hw = _call_gemini_text(google_api_key, crop_text)
            else:
                modality = "vision"
                pil_img = render_crop(pdf_path, page_idx, crop_bbox)
                raw_hw = _call_gemini_vision(google_api_key, pil_img)

            per_detail = _validate_hw(raw_hw)

            # Roll up: total_qty = qty_per_detail (or 1) × callout_count
            total_hw = []
            for item in per_detail:
                qdp   = item["qty_per_detail"] if item["qty_per_detail"] > 0 else 1
                total = qdp * callout_n
                prov  = (
                    f"callout({rec['detail_num']}/{rec['sheet_id']} "
                    f"×{callout_n})"
                )
                total_hw.append({
                    "model":      item["model"],
                    "total_qty":  total,
                    "provenance": prov,
                })

            results.append({
                **base,
                "per_detail_hardware": per_detail,
                "total_hardware": total_hw,
                "modality": modality,
            })
    finally:
        doc.close()

    return results


def rollup_hardware(detail_results: list[dict]) -> list[dict]:
    """Stage 5 input: aggregate total_hardware across all details.

    Merges hardware quantities by model, accumulating total_qty and
    combining provenance strings. Returns a flat list sorted by model.
    """
    totals: dict[str, dict] = {}
    for rec in detail_results:
        for item in rec.get("total_hardware", []):
            model = item["model"]
            if model not in totals:
                totals[model] = {"model": model, "total_qty": 0, "provenance": []}
            totals[model]["total_qty"] += item["total_qty"]
            totals[model]["provenance"].append(item["provenance"])

    return sorted(
        [
            {
                "model": v["model"],
                "total_qty": v["total_qty"],
                "estimated": True,
                "provenance": "; ".join(v["provenance"]),
            }
            for v in totals.values()
        ],
        key=lambda x: x["model"],
    )
