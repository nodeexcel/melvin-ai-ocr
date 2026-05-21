#!/usr/bin/env python3
"""
AI Construction Estimator - Pipeline Test Script

Tests the full pipeline:
  1. Classify all pages using text extraction
  2. Render only relevant pages to images
  3. Extract structured data with GPT-4o Vision
  4. Aggregate into final JSON result

Usage:
  python test_pipeline.py --pdf /path/to/plans.pdf
  python test_pipeline.py --pdf /path/to/plans.pdf --max-pages 20  # for quick testing
"""

import argparse
import base64
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import pypdfium2 as pdfium
from openai import OpenAI
from pdf2image import convert_from_path

# ---------------------------------------------------------------------------
# Classification config
# ---------------------------------------------------------------------------

import re

# Sheet number prefix → category
# Priority: sheet number is extracted from the title block at the end of each page
SHEET_NUMBER_MAP = {
    # Structural — always relevant
    "S0":  "schedules",       # structural general notes
    "S1":  None,              # depends on sheet title (foundation / framing)
    "S2":  "framing_details", # wood framing details

    # Architectural — selectively relevant
    "T0-1": "schedules",      # cover, project info, area calcs
    "T0-2": "schedules",      # general notes, conditions
    "T0-3": "schedules",      # code diagrams, area calculations
    "A1":   "schedules",      # site plan (for project info)
    "A2":   "wall_framing",   # floor plans → wall lengths

    # Everything else → skip
}

# For S1 sheets, further classify by sheet title keywords
S1_TITLE_MAP = {
    "foundation": "foundation",
    "footing":    "foundation",
    "slab":       "foundation",
    "floor fram": "floor_framing",
    "floor jois": "floor_framing",
    "roof fram":  "roof_framing",
    "roof plan":  "roof_framing",
    "shear":      "wall_framing",
    "wall":       "wall_framing",
}

SKIP_PREFIXES = ("L", "M", "E", "P", "C", "A3", "A4", "A5", "A6", "A-", "T0-4", "T0-5")

# Additional sheet number mappings
SHEET_NUMBER_MAP["T0-6"] = "schedules"   # door/window schedules
SHEET_NUMBER_MAP["HD"]   = "schedules"   # Simpson hold-down schedules
# "F" removed — in SVR/Zahn drawings "F1", "F2" etc. mean detail Figure numbers, not Foundation

# Whaleon / Aram Ark structural engineer sheet prefixes (S-1, S-2, S-3, S-4)
SHEET_NUMBER_MAP["S-1"]  = "schedules"      # structural notes
SHEET_NUMBER_MAP["S-2"]  = None             # foundation plan or framing plan — classify by title

# Woodlane Court / LA City standard plan sheets
SHEET_NUMBER_MAP["T1"]   = "framing_details"  # LA City Steel Moment Frame standard plan
SHEET_NUMBER_MAP["S-3"]  = "framing_details"
SHEET_NUMBER_MAP["S-4"]  = "framing_details"

# ---------------------------------------------------------------------------
# Extraction prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a technical document parser for construction drawings. "
    "Extract structured data exactly as shown in the document. "
    "Return valid JSON only — no markdown fences, no explanation, no refusals."
)

EXTRACTION_PROMPTS = {
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def encode_image(image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def extract_page_text(pdf_path: str, page_index: int) -> str:
    """Extract text from a single page using pypdfium2 (fast, low memory)."""
    try:
        doc      = pdfium.PdfDocument(pdf_path)
        page     = doc[page_index]
        textpage = page.get_textpage()
        text     = textpage.get_text_range()
        textpage.close()
        page.close()
        doc.close()
        return text
    except Exception:
        return ""


def extract_sheet_info(text: str) -> tuple:
    """Extract sheet number and sheet title from title block text."""
    # Pattern 5: Ashley & Vance Engineering — "AV JOB:" marker followed by title lines then sheet#
    # e.g. "AV JOB:\r\nFOUNDATION AND\r\nBASEMENT PLANS\r\nS-2.1\r\n..."
    # Run first — very specific marker, prevents CC66/CS14/HDU2 hardware callout false positives
    if 'AV JOB:' in text:
        match5 = re.search(r'AV JOB:\r?\n((?:[^\n\r]*\r?\n){1,4})(S-\d[\d.]*)', text)
        if match5:
            title_raw = match5.group(1).replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').strip()
            sheet_no  = match5.group(2).upper()
            return sheet_no, title_raw.lower()

    # Pattern 3: sheet number near end of text (Aram Ark / Whaleon structural engineer format)
    # e.g. "...A.A. S-2.0 1/4"=1'-0" FOUNDATION PLAN" or "...A.A. S-3.0 N.T.S. TYPICAL DETAILS"
    # Run before Pattern 1 — more specific, avoids false positives on drawing body labels
    match3 = re.search(r'A\.A\.\s+([A-Z]{1,2}-\d[\d\.]*)(.+?)$', text, re.MULTILINE)
    if match3:
        # Title is the trailing run of uppercase words after the scale token(s)
        title_m = re.search(r'([A-Z][A-Z ]{3,})\s*$', match3.group(2))
        if title_m:
            return match3.group(1).upper(), title_m.group(1).strip().lower()

    # Pattern 4: sheet number before "REVISION CLOUD SCHEDULE" at end of text (BARAGHOUSH / letter-firm format)
    # e.g. "...A-4.1 REVISION CLOUD SCHEDULE\r\nREV. MARK..."
    # Run before Pattern 1 — more specific, avoids false positives on drawing body labels
    match4 = re.search(r'([A-Z]{1,2}-\d[\d\.]*)\s+REVISION CLOUD SCHEDULE', text)
    if match4:
        sheet_no = match4.group(1).upper()
        scale_m = re.search(r'SCALE:\s*[^\n\r]+\s+([A-Z][A-Z ]+?)(?:\s+\d+\s*$|\s*$)', text, re.MULTILINE)
        sheet_title = scale_m.group(1).strip().lower() if scale_m else ""
        return sheet_no, sheet_title

    # Pattern 1: sheet number on its own line (BSPK title block)
    # e.g. "CITY DOCUMENTS\r\nT0-400\r\n"
    match = re.search(r'(?:^|[\r\n])([A-Z]{1,3}\d[\d.\-]*\d?)[\r\n]', text)
    if match:
        sheet_no    = match.group(1).upper()
        before      = text[:match.start()].rstrip()
        last_nl     = before.rfind('\n')
        sheet_title = before[last_nl + 1:].strip().lower()
        return sheet_no, sheet_title

    # Pattern 2: sheet number at start of text (landscape/civil title block)
    # e.g. "L0.1 GENERAL NOTES ..."
    match2 = re.match(r'^([A-Z]{1,3}\d[\d.\-]*\d?)\s+(.+?)(?:\r\n|\n|$)', text.strip())
    if match2:
        return match2.group(1).upper(), match2.group(2).strip().lower()

    return "", ""


def classify_page(text: str) -> str:
    """Classify a page based on its sheet number extracted from the title block."""
    sheet_no, sheet_title = extract_sheet_info(text)

    if not sheet_no:
        return "unknown"

    if any(sheet_no.startswith(p) for p in SKIP_PREFIXES):
        return "skip"

    # S1 sheets (SVR/Zahn) — classify further by sheet title
    if sheet_no.startswith("S1"):
        for kw, cat in S1_TITLE_MAP.items():
            if kw in sheet_title:
                return cat
        return "framing_details"

    # S-2 sheets (Whaleon/Aram Ark) — classify further by sheet title
    if sheet_no.startswith("S-2"):
        for kw, cat in S1_TITLE_MAP.items():
            if kw in sheet_title:
                return cat
        return "framing_details"

    # Match remaining prefixes (longest first)
    for prefix in sorted(SHEET_NUMBER_MAP.keys(), key=len, reverse=True):
        if sheet_no.startswith(prefix):
            result = SHEET_NUMBER_MAP[prefix]
            return result if result else "unknown"

    return "unknown"


TEXT_HEAVY_MIN_CHARS = 2000  # pages with more than this many chars use text extraction, not Vision

# Categories where the key data is in graphical drawings — always use Vision regardless of text content
# wall_framing (A2 RCP pages) excluded: Vision hallucinates/refuses, text extraction is more reliable
VISION_ONLY_CATEGORIES = {"floor_framing", "roof_framing", "foundation"}


def is_text_heavy(text: str, category: str) -> bool:
    """True when the page should use text extraction instead of Vision."""
    if category in VISION_ONLY_CATEGORIES:
        return False
    # Schedules pages: title block fields are always in the text layer — prefer text over Vision
    # which tends to read sheet content (notes, tables) instead of the title block.
    if category == "schedules" and len(text.strip()) > 100:
        return True
    return len(text.strip()) > TEXT_HEAVY_MIN_CHARS


def _parse_gpt_response(content: str, usage):
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1].lstrip("json").strip() if len(parts) > 1 else content
    try:
        return json.loads(content), usage
    except json.JSONDecodeError:
        return {"raw_response": content, "parse_error": True}, usage


def extract_with_gpt4o(client: OpenAI, image, category: str) -> dict:
    prompt = EXTRACTION_PROMPTS.get(category, EXTRACTION_PROMPTS["schedules"])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(image)}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=8000,
        temperature=0,
    )

    content = response.choices[0].message.content.strip()
    return _parse_gpt_response(content, response.usage)


def extract_with_gpt4o_text(client: OpenAI, text: str, category: str) -> dict:
    """Extract structured data from raw pypdfium2 text — no image, no hallucination."""
    prompt = EXTRACTION_PROMPTS.get(category, EXTRACTION_PROMPTS["schedules"])
    full_prompt = f"{prompt}\n\nDocument text:\n{text}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt},
        ],
        max_tokens=8000,
        temperature=0,
    )

    content = response.choices[0].message.content.strip()
    return _parse_gpt_response(content, response.usage)


def aggregate_results(extractions: list) -> dict:
    result = {
        "project": {"name": "", "address": "", "architect": "", "structural_engineer": "", "total_sqft": 0, "sheet_list": []},
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
            # Merge each field independently — keep the best value seen across all schedule pages
            if data.get("project_name") and not proj.get("name"):
                proj["name"] = data["project_name"]
            if data.get("project_address") and not proj.get("address"):
                proj["address"] = data["project_address"]
            if data.get("architect") and not proj.get("architect"):
                proj["architect"] = data["architect"]
            if data.get("structural_engineer") and not proj.get("structural_engineer"):
                proj["structural_engineer"] = data["structural_engineer"]
            if data.get("total_sqft") and data["total_sqft"] > proj.get("total_sqft", 0):
                proj["total_sqft"] = data["total_sqft"]
            # Keep the longest sheet_list seen
            new_sheets = data.get("sheet_list") or []
            if len(new_sheets) > len(proj.get("sheet_list") or []):
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
        result["foundation"].get("hold_downs", []) +
        result["floor_framing"].get("hardware", []) +
        result["wall_framing"].get("hardware", []) +
        result["roof_framing"].get("hardware", []) +
        [item for item in result["framing_details"] if "model" in item]
    )

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AI Construction Estimator — Pipeline Test")
    parser.add_argument("--pdf",       required=True,        help="Path to input PDF")
    parser.add_argument("--output",    default="output",     help="Output directory (default: output)")
    parser.add_argument("--dpi",       type=int, default=250, help="Render DPI (default: 250)")
    parser.add_argument("--max-pages", type=int, default=None, help="Cap page count for quick tests")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    client     = OpenAI(api_key=api_key)
    start_time = time.time()

    print(f"\nProcessing: {pdf_path.name}")
    print("=" * 60)

    # ── Step 1: Count pages ──────────────────────────────────────────────────
    doc         = pdfium.PdfDocument(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    if args.max_pages:
        total_pages = min(total_pages, args.max_pages)

    print(f"\n[1/4] Classifying {total_pages} pages...")

    classifications = []
    for i in range(total_pages):
        text            = extract_page_text(str(pdf_path), i)
        category        = classify_page(text)
        sheet_no, title = extract_sheet_info(text)
        use_text        = is_text_heavy(text, category) and category not in ("skip", "unknown")
        classifications.append({
            "page": i + 1, "category": category, "sheet_no": sheet_no,
            "text": text, "use_text": use_text,
        })
        if category not in ("skip", "unknown"):
            method = "text" if use_text else "vision"
            print(f"      Page {i+1:3d}  {sheet_no:10s}  → {category}  [{method}]")
        elif category == "skip":
            print(f"      Page {i+1:3d}  {sheet_no:10s}  → skip")

    relevant     = [p for p in classifications if p["category"] not in ("skip", "unknown")]
    skipped      = [p for p in classifications if p["category"] == "skip"]
    unknown      = [p for p in classifications if p["category"] == "unknown"]
    vision_pages = [p for p in relevant if not p["use_text"]]
    text_pages   = [p for p in relevant if p["use_text"]]

    print(f"\n      Relevant: {len(relevant)}  "
          f"({len(text_pages)} text / {len(vision_pages)} vision)  |  "
          f"Skipped: {len(skipped)}  |  Unknown: {len(unknown)}")

    if not relevant:
        print("\nNo relevant pages found. Check classification keywords.")
        sys.exit(1)

    # ── Step 2: Render vision-only pages ────────────────────────────────────
    print(f"\n[2/4] Rendering {len(vision_pages)} pages to images (DPI={args.dpi})...")

    page_images = {}
    for i, page_info in enumerate(vision_pages):
        page_num = page_info["page"]
        images   = convert_from_path(
            str(pdf_path), dpi=args.dpi,
            first_page=page_num, last_page=page_num,
        )
        page_images[page_num] = images[0]
        print(f"      {i+1}/{len(vision_pages)} — page {page_num}", end="\r")

    if vision_pages:
        print(f"      Rendered {len(page_images)} pages                          ")
    else:
        print(f"      All relevant pages are text-heavy — skipping rendering")

    # ── Step 3: Extract with GPT-4o ─────────────────────────────────────────
    print(f"\n[3/4] Extracting data ({len(text_pages)} text + {len(vision_pages)} vision)...")

    extractions  = []
    total_tokens = {"prompt": 0, "completion": 0}

    for page_info in relevant:
        page_num = page_info["page"]
        category = page_info["category"]

        print(f"      Page {page_num:3d} ({category})...", end=" ", flush=True)

        try:
            if page_info["use_text"]:
                data, usage = extract_with_gpt4o_text(client, page_info["text"], category)
                method = "text"
            else:
                image = page_images.get(page_num)
                if image is None:
                    print("✗  image missing")
                    continue
                data, usage = extract_with_gpt4o(client, image, category)
                method = "vision"

            extractions.append({"page": page_num, "category": category, "data": data, "method": method})
            total_tokens["prompt"]     += usage.prompt_tokens
            total_tokens["completion"] += usage.completion_tokens
            status = "✓" if not data.get("parse_error") else "⚠ parse_error"
            print(status)
        except Exception as e:
            print(f"✗  {e}")
            extractions.append({"page": page_num, "category": category, "data": {"error": str(e)}, "method": "error"})

    # ── Step 4: Aggregate and save ───────────────────────────────────────────
    print(f"\n[4/4] Aggregating results...")

    final = aggregate_results(extractions)

    elapsed     = time.time() - start_time
    stem        = pdf_path.stem.replace(" ", "_")
    output_file = output_dir / f"{stem}_results.json"

    with open(output_file, "w") as f:
        json.dump(final, f, indent=2)

    # Rough cost estimate (GPT-4o pricing as of 2025)
    cost = (total_tokens["prompt"] / 1_000_000 * 5.0) + (total_tokens["completion"] / 1_000_000 * 15.0)

    print(f"\n{'=' * 60}")
    print(f"  Output:     {output_file}")
    print(f"  Time:       {elapsed / 60:.1f} min")
    print(f"  Pages:      {len(extractions)} processed / {total_pages} total")
    print(f"  Tokens:     {total_tokens['prompt']:,} in  /  {total_tokens['completion']:,} out")
    print(f"  Est. cost:  ~${cost:.2f}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
