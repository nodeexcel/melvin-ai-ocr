#!/usr/bin/env python3
"""
Raster PDF pipeline — for scanned/stamped plans with no text layer.

Two-phase approach:
  Phase 1 — Classify all pages via batched thumbnail Vision calls (cheap).
             Each API call sends 4 thumbnails and asks for sheet# + category.
  Phase 2 — Extract structural data from relevant pages at full resolution.

Usage:
  python test_pipeline_raster.py --pdf /path/to/plans.pdf
  python test_pipeline_raster.py --pdf /path/to/plans.pdf --classify-only
"""

import argparse
import base64
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

THUMBNAIL_WIDTH_PX  = 700     # width for classification thumbnails
THUMBNAIL_QUALITY   = 70      # JPEG quality for thumbnails
EXTRACT_DPI_SCALE   = 2.5     # ~180 DPI for extraction (scale=1 → 72 DPI)
PAGES_PER_BATCH     = 4       # pages per classification API call
MAX_TOKENS_CLASSIFY = 1000    # classification response is just JSON
MAX_TOKENS_EXTRACT  = 8000    # extraction needs room for full data

# Structural categories we care about
STRUCTURAL_CATEGORIES = {"structural_notes", "foundation", "framing_plan", "framing_details"}

# Map Vision-identified category to extraction prompt key
CATEGORY_TO_PROMPT = {
    "structural_notes": "schedules",
    "foundation":       "foundation",
    "framing_plan":     "floor_framing",
    "framing_details":  "framing_details",
}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a technical document parser for construction drawings. "
    "Extract structured data exactly as shown in the document. "
    "Return valid JSON only — no markdown fences, no explanation, no refusals. "
    "If the image is a graphical drawing with no readable spec text, return the schema with empty arrays and zero values."
)

CLASSIFY_PROMPT = """These are thumbnail images of architectural/engineering plan sheets.
For each image (labeled Image 1, Image 2, etc.), find the sheet number in the title block
(usually bottom-right corner) and classify the sheet.

Return a JSON array with one object per image:
[
  {
    "image": 1,
    "sheet_no": "SN1",
    "sheet_title": "structural notes",
    "category": "structural_notes"
  },
  ...
]

Categories (pick exactly one):
- "structural_notes"  — general structural notes, specifications, schedules, nailing schedules
- "foundation"        — foundation plan, footing plan, slab plan, foundation details
- "framing_plan"      — floor framing plan, roof framing plan, shear wall plan
- "framing_details"   — structural connection details, steel details, wood details
- "civil"             — topographic survey, grading plan, utility plan
- "architectural"     — floor plan, elevation, section, ceiling plan, door/window schedule, site plan
- "skip"              — anything not construction drawings (cover sheet info pages, assessor data, photos)

If the sheet number is not visible or unclear, use "" for sheet_no and make your best category guess."""

EXTRACTION_PROMPTS = {
    "schedules": """This is a structural general notes or specifications sheet (raster image).
Extract ALL of the following as JSON:
{
  "project_name": "",
  "project_address": "",
  "architect": "",
  "structural_engineer": "",
  "total_sqft": 0,
  "sheet_list": [{"sheet_no": "", "title": ""}],
  "lumber_specs": [],
  "concrete_specs": [],
  "nailing_schedule": [],
  "fastening_schedule": [],
  "notes": []
}
IMPORTANT: For project_name, project_address, architect, structural_engineer — return exactly what is printed in the title block. If these fields show placeholder text (e.g. "PROJECT DESCRIPTION", "OWNER", "ARCHITECT") or are illegible, return empty string. Never invent or guess addresses, names, or firm names.""",

    "foundation": """This is a foundation plan or footing detail sheet (raster image).
Extract ALL of the following as JSON:
{
  "footing_types": [{"type": "", "width_in": 0, "depth_in": 0, "linear_feet": 0}],
  "concrete_cubic_yards": 0,
  "rebar": [{"size": "", "spacing_in": 0, "linear_feet": 0, "qty_pieces": 0}],
  "anchor_bolts": {"size": "", "spacing_in": 0, "qty": 0},
  "hold_downs": [{"model": "", "qty": 0}],
  "notes": []
}""",

    "floor_framing": """This is a floor or roof framing plan (raster image).
Extract ALL of the following as JSON:
{
  "joists": [{"size": "", "spacing_in": 0, "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}],
  "beams": [{"size": "", "span_ft": 0, "linear_feet": 0, "qty_pieces": 0}],
  "posts": [{"size": "", "height_ft": 0, "qty": 0}],
  "blocking": {"size": "", "linear_feet": 0},
  "hardware": [{"model": "", "qty": 0}],
  "notes": []
}""",

    "framing_details": """This is a structural framing or connection detail sheet (raster image).
Extract ALL of the following as JSON:
{
  "connections": [{"description": "", "hardware": "", "lumber_sizes": [], "steel_sizes": []}],
  "hardware": [{"model": "", "description": "", "qty_mentioned": 0}],
  "steel_members": [{"type": "", "size": "", "description": ""}],
  "special_conditions": [],
  "notes": []
}""",
}

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_thumbnail(doc: pdfium.PdfDocument, page_index: int) -> bytes:
    """Render page to a small JPEG thumbnail for classification."""
    page    = doc[page_index]
    bitmap  = page.render(scale=1.0)
    img     = bitmap.to_pil()
    page.close()

    # Resize to THUMBNAIL_WIDTH_PX wide
    orig_w, orig_h = img.size
    new_h = int(orig_h * THUMBNAIL_WIDTH_PX / orig_w)
    img   = img.resize((THUMBNAIL_WIDTH_PX, new_h))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=THUMBNAIL_QUALITY)
    return buf.getvalue()


def render_full(doc: pdfium.PdfDocument, page_index: int) -> bytes:
    """Render page at extraction DPI as JPEG."""
    page   = doc[page_index]
    bitmap = page.render(scale=EXTRACT_DPI_SCALE)
    img    = bitmap.to_pil()
    page.close()

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def to_b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ---------------------------------------------------------------------------
# Phase 1 — Classification
# ---------------------------------------------------------------------------

def classify_batch(client: OpenAI, pages: list[dict]) -> list[dict]:
    """
    Classify a batch of pages via Vision.
    Each item in `pages` is {"page_num": int, "image_bytes": bytes}.
    Returns list of {"page_num", "sheet_no", "sheet_title", "category"}.
    """
    content = [{"type": "text", "text": CLASSIFY_PROMPT}]
    for idx, p in enumerate(pages):
        content.append({
            "type": "text",
            "text": f"Image {idx + 1} (PDF page {p['page_num']}):"
        })
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{to_b64(p['image_bytes'])}",
                "detail": "low",
            },
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": content},
        ],
        max_tokens=MAX_TOKENS_CLASSIFY,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw   = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    try:
        results = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [WARN] Classification parse error: {raw[:200]}")
        results = [{"image": i + 1, "sheet_no": "", "sheet_title": "", "category": "unknown"}
                   for i in range(len(pages))]

    output = []
    for item in results:
        img_idx  = item.get("image", 1) - 1
        page_num = pages[img_idx]["page_num"] if img_idx < len(pages) else -1
        output.append({
            "page_num":    page_num,
            "sheet_no":    item.get("sheet_no", ""),
            "sheet_title": item.get("sheet_title", ""),
            "category":    item.get("category", "unknown"),
        })
    return output


def classify_all_pages(client: OpenAI, pdf_path: str) -> list[dict]:
    """Classify all pages in a raster PDF using batched thumbnail Vision calls."""
    doc        = pdfium.PdfDocument(pdf_path)
    total      = len(doc)
    all_pages  = list(range(total))
    results    = []

    print(f"Classifying {total} pages in batches of {PAGES_PER_BATCH}...")

    for batch_start in range(0, total, PAGES_PER_BATCH):
        batch_indices = all_pages[batch_start:batch_start + PAGES_PER_BATCH]
        batch_pages   = []

        for i in batch_indices:
            thumb = render_thumbnail(doc, i)
            batch_pages.append({"page_num": i + 1, "image_bytes": thumb})

        page_range = f"{batch_indices[0]+1}–{batch_indices[-1]+1}"
        print(f"  Classifying pages {page_range}...", flush=True)

        classified = classify_batch(client, batch_pages)
        results.extend(classified)

        # Small delay to avoid rate limits
        if batch_start + PAGES_PER_BATCH < total:
            time.sleep(0.5)

    doc.close()
    return results


# ---------------------------------------------------------------------------
# Phase 2 — Extraction
# ---------------------------------------------------------------------------

def _parse_gpt_response(content: str, usage):
    if content.startswith("```"):
        parts   = content.split("```")
        content = parts[1].lstrip("json").strip() if len(parts) > 1 else content
    try:
        return json.loads(content), usage
    except json.JSONDecodeError:
        return {"raw_response": content, "parse_error": True}, usage


def extract_page(client: OpenAI, image_bytes: bytes, category: str, prompt_key: str) -> dict:
    """Extract structural data from a raster page via Vision."""
    prompt = EXTRACTION_PROMPTS.get(prompt_key, EXTRACTION_PROMPTS["framing_details"])

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
                            "url": f"data:image/jpeg;base64,{to_b64(image_bytes)}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=MAX_TOKENS_EXTRACT,
        temperature=0,
    )

    content = response.choices[0].message.content.strip()
    data, usage = _parse_gpt_response(content, response.usage)
    return data, usage


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_results(extractions: list[dict]) -> dict:
    result = {
        "project": {
            "name": "", "address": "", "architect": "",
            "structural_engineer": "", "total_sqft": 0, "sheet_list": [],
        },
        "foundation":       {"footing_types": [], "rebar": [], "anchor_bolts": {}, "hold_downs": [], "concrete_cubic_yards": 0},
        "floor_framing":    {"joists": [], "beams": [], "posts": [], "blocking": {}, "hardware": []},
        "framing_details":  {"connections": [], "hardware": [], "steel_members": []},
        "schedules":        {"lumber_specs": [], "concrete_specs": [], "nailing_schedule": [], "fastening_schedule": []},
    }

    for entry in extractions:
        cat  = entry["category"]
        data = entry["data"]
        if isinstance(data, dict) and data.get("parse_error"):
            continue

        if cat == "schedules":
            proj = result["project"]
            if data.get("project_name")       and not proj["name"]:             proj["name"]               = data["project_name"]
            if data.get("project_address")    and not proj["address"]:          proj["address"]            = data["project_address"]
            if data.get("architect")          and not proj["architect"]:         proj["architect"]          = data["architect"]
            if data.get("structural_engineer") and not proj["structural_engineer"]: proj["structural_engineer"] = data["structural_engineer"]
            if data.get("total_sqft", 0) > proj["total_sqft"]:                  proj["total_sqft"]         = data["total_sqft"]
            new_sheets = data.get("sheet_list") or []
            if len(new_sheets) > len(proj["sheet_list"]):                        proj["sheet_list"]         = new_sheets

            sched = result["schedules"]
            sched["lumber_specs"]      += data.get("lumber_specs", [])      or []
            sched["concrete_specs"]    += data.get("concrete_specs", [])    or []
            sched["nailing_schedule"]  += data.get("nailing_schedule", [])  or []
            sched["fastening_schedule"]+= data.get("fastening_schedule", []) or []

        elif cat == "foundation":
            fd = result["foundation"]
            fd["footing_types"] += data.get("footing_types", []) or []
            fd["rebar"]         += data.get("rebar", [])         or []
            fd["hold_downs"]    += data.get("hold_downs", [])    or []
            if data.get("anchor_bolts") and not fd["anchor_bolts"]:
                fd["anchor_bolts"]  = data["anchor_bolts"]
            if data.get("concrete_cubic_yards", 0) > 0:
                fd["concrete_cubic_yards"] = data["concrete_cubic_yards"]

        elif cat in ("floor_framing", "framing_plan"):
            ff = result["floor_framing"]
            ff["joists"]   += data.get("joists", [])   or []
            ff["beams"]    += data.get("beams", [])    or []
            ff["posts"]    += data.get("posts", [])    or []
            ff["hardware"] += data.get("hardware", []) or []

        elif cat == "framing_details":
            fd = result["framing_details"]
            fd["connections"]   += data.get("connections", [])   or []
            fd["hardware"]      += data.get("hardware", [])      or []
            fd["steel_members"] += data.get("steel_members", []) or []

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf",           required=True)
    parser.add_argument("--classify-only", action="store_true", help="Stop after classification")
    parser.add_argument("--max-pages",     type=int, default=None)
    parser.add_argument("--rerun-pages",   type=str, default=None,
                        help="Comma-separated page numbers to re-extract (skips classification, uses saved JSON)")
    args = parser.parse_args()

    client   = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    pdf_path = args.pdf
    pdf_name = Path(pdf_path).stem.replace(" ", "_")
    out_dir  = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)

    t0 = time.time()

    # ---- Phase 1: Classify (or load saved) ----
    saved_classify = out_dir / f"{pdf_name}_classification.json"
    if args.rerun_pages and saved_classify.exists():
        print(f"Loading saved classification from {saved_classify}")
        with open(saved_classify) as f:
            classification = json.load(f)
        rerun_nums = {int(x.strip()) for x in args.rerun_pages.split(",")}
        classification = [r for r in classification if r["page_num"] in rerun_nums]
        for r in classification:
            r["category"] = r.get("category", "unknown")
        print(f"Re-running extraction on pages: {sorted(rerun_nums)}")
    else:
        classification = classify_all_pages(client, pdf_path)

    if args.max_pages:
        classification = classification[:args.max_pages]

    print("\n--- Classification Results ---")
    for r in classification:
        flag = "★" if r["category"] in STRUCTURAL_CATEGORIES else " "
        print(f"  {flag} Page {r['page_num']:3d}  {r['sheet_no']:8s}  {r['sheet_title'][:35]:35s}  {r['category']}")

    structural_pages = [r for r in classification if r["category"] in STRUCTURAL_CATEGORIES]
    print(f"\nStructural pages found: {len(structural_pages)}")

    classify_out = out_dir / f"{pdf_name}_classification.json"
    with open(classify_out, "w") as f:
        json.dump(classification, f, indent=2)
    print(f"Classification saved → {classify_out}")

    if args.classify_only or not structural_pages:
        print("\nDone (classify-only mode).")
        return

    # ---- Phase 2: Extract ----
    print("\n--- Extracting structural pages ---")
    doc         = pdfium.PdfDocument(pdf_path)
    extractions = []
    total_cost_tokens = 0

    for page_info in structural_pages:
        page_idx    = page_info["page_num"] - 1
        category    = page_info["category"]
        prompt_key  = CATEGORY_TO_PROMPT.get(category, "framing_details")
        sheet_no    = page_info["sheet_no"]

        print(f"  Extracting page {page_info['page_num']} ({sheet_no}) — {category}...", flush=True)
        image_bytes = render_full(doc, page_idx)
        data, usage = extract_page(client, image_bytes, category, prompt_key)

        total_cost_tokens += (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)

        parse_ok = not (isinstance(data, dict) and data.get("parse_error"))
        print(f"    {'✅' if parse_ok else '❌'} tokens: {usage.prompt_tokens}+{usage.completion_tokens}")

        extractions.append({
            "page_num":    page_info["page_num"],
            "sheet_no":    sheet_no,
            "sheet_title": page_info["sheet_title"],
            "category":    prompt_key,
            "data":        data,
        })

    doc.close()

    # ---- Aggregate ----
    aggregated = aggregate_results(extractions)
    elapsed    = time.time() - t0

    output = {
        "pdf":            Path(pdf_path).name,
        "total_pages":    len(classification),
        "structural_pages": len(structural_pages),
        "elapsed_sec":    round(elapsed, 1),
        "result":         aggregated,
        "pages":          extractions,
    }

    out_file = out_dir / f"{pdf_name}_results.json"
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n--- Complete ---")
    print(f"  Time:    {elapsed:.1f}s")
    print(f"  Pages:   {len(structural_pages)} structural / {len(classification)} total")
    print(f"  Output:  {out_file}")
    print(f"  Project: {aggregated['project']['name']}")
    print(f"  Address: {aggregated['project']['address']}")
    print(f"  Structural engineer: {aggregated['project']['structural_engineer']}")


if __name__ == "__main__":
    main()
