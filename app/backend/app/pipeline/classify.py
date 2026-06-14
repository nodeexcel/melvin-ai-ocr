"""
Vision-first page classification using gpt-4o-mini.

Every page is classified by rendering a low-res thumbnail and asking the model
what type of sheet it is. No hardcoded patterns, no firm-specific logic, no
binary raster/digital detection. Works for any SE firm, any page ordering,
any PDF type (digital, scanned, or mixed).

Text extraction is still used for the EXTRACTION phase when a page has a
dense text layer — Vision only replaces CLASSIFICATION.
"""

import base64
import json
import time
from collections.abc import Callable
from io import BytesIO

import pypdfium2 as pdfium
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

THUMBNAIL_WIDTH_PX  = 700
THUMBNAIL_QUALITY   = 70
PAGES_PER_BATCH     = 4
CLASSIFY_MODEL      = "gpt-4o-mini"
MAX_TOKENS_CLASSIFY = 500

# Pages in these categories always use Vision for extraction, even if text-heavy
VISION_ONLY_CATEGORIES = {"floor_framing", "roof_framing", "foundation"}

# Minimum chars to consider a page text-heavy enough for text extraction
TEXT_HEAVY_MIN_CHARS = 2000

# Vision classifier category → pipeline category
CATEGORY_MAP: dict[str, str] = {
    "structural_notes": "schedules",
    "foundation":       "foundation",
    "floor_framing":    "floor_framing",
    "roof_framing":     "roof_framing",
    "wall_framing":     "wall_framing",
    "framing_details":  "framing_details",
    "civil":            "skip",
    "architectural":    "skip",
    "skip":             "skip",
    "unknown":          "unknown",
}

# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a technical document parser for construction drawings. "
    "Return valid JSON only — no markdown fences, no explanation, no refusals."
)

_CLASSIFY_PROMPT = """These are thumbnail images of architectural/engineering plan sheets.
For each image (labeled Image 1, Image 2, etc.), identify the sheet type.

Return a JSON array with one object per image:
[{"image": 1, "sheet_no": "S1", "category": "structural_notes"}, ...]

KEY VISUAL RULE: If a sheet shows a large overhead PLAN VIEW of the entire building
(you can see the building's overall footprint, floor layout, or roof layout from above),
classify it as foundation / floor_framing / roof_framing / wall_framing — even if it
also has detail callouts, hold-down schedules, or connection symbols on the side.
Only use "framing_details" when the sheet contains ONLY small isolated connection
diagrams without any overall building plan view.

Categories — pick exactly one per sheet:
- "structural_notes"  — general structural notes, specifications, schedules, nailing schedules, title sheets with structural data
- "foundation"        — foundation PLAN (overhead view of building footprint showing footing/slab layout), footing plan, slab plan, grade beam plan
- "floor_framing"     — floor framing PLAN (overhead view showing joist/beam layout across the floor), floor joist plan, floor beam plan
- "roof_framing"      — roof framing PLAN (overhead view showing rafter/beam layout across the roof), roof joist plan, rafter plan, roof beam layout
- "wall_framing"      — shear wall plan, wall framing plan, wall schedule, lateral force plan (overhead view)
- "framing_details"   — sheet containing ONLY small isolated structural connection details, steel details, hold-down details, hardware callouts — NO overall building plan view
- "civil"             — topographic survey, grading plan, utility plan, drainage plan
- "architectural"     — floor plan, elevation, building section, ceiling plan, door/window schedule, finish schedule, site plan
- "skip"              — cover sheet, title 24 energy forms, assessor parcel data, photos, general contractor notes, non-structural admin pages

Use "" for sheet_no if the sheet number is not clearly visible."""

# ── Rendering ─────────────────────────────────────────────────────────────────

def _render_thumbnail(doc: pdfium.PdfDocument, page_index: int) -> bytes:
    page   = doc[page_index]
    bitmap = page.render(scale=1.0)
    img    = bitmap.to_pil()
    page.close()

    orig_w, orig_h = img.size
    new_h = int(orig_h * THUMBNAIL_WIDTH_PX / orig_w)
    img   = img.resize((THUMBNAIL_WIDTH_PX, new_h))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=THUMBNAIL_QUALITY)
    return buf.getvalue()


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode()


# ── Batch Vision classification ───────────────────────────────────────────────

def _classify_batch(client: OpenAI, batch: list[dict]) -> list[dict]:
    """
    Classify one batch of pages.
    batch: [{"page_num": int, "image_bytes": bytes}]
    Returns: [{"page_num": int, "sheet_no": str, "category": str}]
    """
    content: list[dict] = [{"type": "text", "text": _CLASSIFY_PROMPT}]
    for idx, p in enumerate(batch):
        content.append({"type": "text", "text": f"Image {idx + 1} (PDF page {p['page_num']}):"})
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{_b64(p['image_bytes'])}",
                "detail": "low",
            },
        })

    response = client.chat.completions.create(
        model=CLASSIFY_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": content},
        ],
        max_tokens=MAX_TOKENS_CLASSIFY,
        temperature=0,
    )

    raw = (response.choices[0].message.content or "").strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        items = [{"image": i + 1, "sheet_no": "", "category": "unknown"}
                 for i in range(len(batch))]

    results = []
    for item in items:
        img_idx  = item.get("image", 1) - 1
        page_num = batch[img_idx]["page_num"] if img_idx < len(batch) else batch[0]["page_num"]
        raw_cat  = item.get("category", "unknown")
        results.append({
            "page_num":  page_num,
            "sheet_no":  item.get("sheet_no", ""),
            "category":  CATEGORY_MAP.get(raw_cat, "unknown"),
        })
    return results


# ── Text cross-check ─────────────────────────────────────────────────────────

# Title phrases that confirm a page is a foundation plan.
# Used as fallback when Vision misclassifies foundation plan pages.
_FOUNDATION_PLAN_PHRASES = [
    "FOUNDATION PLAN",
    "FOOTING PLAN",
    "GRADE BEAM PLAN",
    "SLAB PLAN",
]

# Phrases that ONLY appear in structural spec/schedule pages — never in
# graphical framing plans, foundation plans, or architectural drawings.
# Used to correct Vision misclassifications on text-dense pages.
_SCHEDULE_PHRASES = [
    "NAILING SCHEDULE",
    "NAILING REQUIREMENTS",
    "LUMBER SPECIFICATIONS",
    "LUMBER SCHEDULE",
    "CONCRETE SPECIFICATIONS",
    "CONCRETE SCHEDULE",
    "GENERAL STRUCTURAL NOTES",
    "STRUCTURAL SPECIFICATIONS",
    "STRUCTURAL GENERAL NOTES",
    "SHANK DIAMETER",        # nail spec tables always contain this
    "COMMON WIRE NAILS",     # nailing schedule header text
    "DOUGLAS FIR - LARCH",   # lumber spec text
    "DOUGLAS FIR-LARCH",
    "DOUGLAS FIR - COSTAL",
]


def _text_schedule_override(text: str) -> bool:
    """
    Return True if the text layer strongly signals this is a structural
    spec/schedule page, regardless of what Vision classified it as.

    Only fires on unambiguous phrases that cannot appear on graphical plan
    pages (framing plans, foundation plans, elevation sheets).
    """
    text_upper = text.upper()
    return any(phrase in text_upper for phrase in _SCHEDULE_PHRASES)


# ── Public API ────────────────────────────────────────────────────────────────

def is_text_heavy(text: str, category: str) -> bool:
    """True when the page should use text extraction instead of Vision."""
    if category in VISION_ONLY_CATEGORIES:
        return False
    if category == "schedules" and len(text.strip()) > 100:
        return True
    return len(text.strip()) > TEXT_HEAVY_MIN_CHARS


def classify_pages(
    client: OpenAI,
    pdf_path: str,
    on_progress: Callable[[str, str, int], None],
) -> list[dict]:
    """
    Classify every page in the PDF via Vision thumbnails using gpt-4o-mini.

    Returns a list in the same format expected by render_vision_pages() and
    extract_all_pages() in runner.py:
    [{"page": N, "category": cat, "sheet_no": str, "text": str, "use_text": bool}]

    Works for any PDF type — digital, scanned, or mixed pages within the same file.
    """
    doc   = pdfium.PdfDocument(pdf_path)
    total = len(doc)

    on_progress("classifying", f"Classifying {total} pages via Vision...", 8)

    pages: list[dict] = []

    try:
        for batch_start in range(0, total, PAGES_PER_BATCH):
            batch_end     = min(batch_start + PAGES_PER_BATCH, total)
            batch_indices = list(range(batch_start, batch_end))

            # Render thumbnails + read text layer for this batch
            batch_items = []
            batch_texts = []
            for i in batch_indices:
                thumb = _render_thumbnail(doc, i)
                batch_items.append({"page_num": i + 1, "image_bytes": thumb})

                page_obj = doc[i]
                tp = page_obj.get_textpage()
                batch_texts.append(tp.get_text_range())
                tp.close()
                page_obj.close()

            # Vision classify this batch
            results = _classify_batch(client, batch_items)

            # Build page dicts
            for j, result in enumerate(results):
                text = batch_texts[j] if j < len(batch_texts) else ""
                cat  = result["category"]

                # Two-signal correction: if Vision classified this as a
                # graphical plan type but the text layer has unambiguous
                # schedule/spec phrases, trust the text signal.
                if (
                    cat in ("foundation", "floor_framing", "roof_framing", "wall_framing", "unknown")
                    and len(text.strip()) > 500
                    and _text_schedule_override(text)
                ):
                    cat = "schedules"

                # Foundation plan override: if the text layer contains an
                # unambiguous foundation plan title and Vision missed it,
                # correct the category. Only fires when not already schedules
                # (schedule override already ran above and takes precedence).
                if cat not in ("foundation", "schedules", "skip") and text:
                    text_upper = text.upper()
                    if any(p in text_upper for p in _FOUNDATION_PLAN_PHRASES):
                        cat = "foundation"

                pages.append({
                    "page":     result["page_num"],
                    "category": cat,
                    "sheet_no": result["sheet_no"],
                    "text":     text,
                    "use_text": is_text_heavy(text, cat) and cat not in ("skip", "unknown"),
                })

            # Progress: classification runs from 8% to 35%
            done_pct = 8 + int((batch_end / total) * 27)
            on_progress(
                "classifying",
                f"Classified {batch_end}/{total} pages",
                min(done_pct, 35),
            )

            if batch_end < total:
                time.sleep(0.3)

    finally:
        doc.close()

    return pages
