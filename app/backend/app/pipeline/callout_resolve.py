"""Stage 3 of the callout engine: resolve (detail_num, sheet_id) → page + bbox.

Given the callout counts from stage 2 (callout.py), this module locates the
matching detail box on the detail-sheet pages of the same PDF.

Output feeds stage 4: each located detail becomes a crop region for hardware
extraction (text-layer or vision, depending on page modality).

Design rules (from spike on 8603 Rugby / Terra Nova):
  • Pass ONLY detail-sheet page indices (framing_details from classify.py).
    Plan pages also contain SDx tokens as callout references — they must be
    excluded to avoid false matches.
  • CAD detail sheets store headers as inline "SD1 1" text objects (space) OR
    as split objects "SD1\\n8B" (sheet and number in separate text runs).
    We try both separators; the first hit wins.
  • Multiple identical headers on one page = the same detail label appears more
    than once (e.g. a mirrored detail or repeated title).  We keep the first
    occurrence (lowest char index in the text stream = top-of-page).
  • bbox is the tight box of the header text only.  Stage 4 callers should
    expand it downward/rightward to capture the full detail drawing content.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

import pypdfium2 as pdfium


# ── Public types ────────────────────────────────────────────────────────────────

class DetailLocation(TypedDict):
    page_index: int          # 0-based page index in the PDF
    bbox: tuple[float, float, float, float]   # (x0, y0, x1, y1) in PDF pts (y=0 at bottom)
    header_text: str         # raw text of the header token as found


DetailMap = dict[tuple[str, str], DetailLocation]   # key: (detail_num, sheet_id)


# ── Core helpers ────────────────────────────────────────────────────────────────

def _charboxes_union(textpage, start: int, length: int) -> tuple[float, float, float, float]:
    """Return the union bounding box of characters [start, start+length)."""
    xs: list[float] = []
    ys: list[float] = []
    for i in range(start, start + length):
        x0, y0, x1, y1 = textpage.get_charbox(i)
        xs += [x0, x1]
        ys += [y0, y1]
    return (min(xs), min(ys), max(xs), max(ys))


def _search_header(textpage, sheet_id: str, detail_num: str) -> tuple[int, int] | None:
    """Find the first occurrence of a detail header on this textpage.

    Tries:
      1. Inline:  "SD1 1"   (space separator — most common)
      2. Split:   "SD1\\n1" (newline separator — some CAD text runs)
      3. Inline uppercase variant (case-normalised)
    Returns (char_start, length) or None.
    """
    for sep in (" ", "\n"):
        needle = f"{sheet_id}{sep}{detail_num}"
        result = textpage.search(needle, match_whole_word=False)
        occ = result.get_next()
        if occ:
            return occ
        # try uppercase
        needle_up = needle.upper()
        if needle_up != needle:
            result = textpage.search(needle_up, match_whole_word=False)
            occ = result.get_next()
            if occ:
                return occ
    return None


# ── Public API ──────────────────────────────────────────────────────────────────

def build_detail_map(
    pdf_path: str | Path,
    detail_page_indices: list[int],
) -> DetailMap:
    """Scan detail-sheet pages and build a map from (detail_num, sheet_id) → location.

    Pass ONLY detail-sheet page indices (not plan pages).

    Returns a dict keyed by (detail_num, sheet_id).
    Duplicates on the same page (same header appearing twice) keep the first hit.
    If the same pair appears on multiple pages, the earliest page wins.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    # Pattern: "SD1 1", "SD1 7A", "SD3 20" — inline or split across newline
    HEADER_RE = re.compile(r"(SD\d+[A-Z]?|S\d+[A-Z]?)\s+(\d+[A-Z]?)\b", re.IGNORECASE)

    detail_map: DetailMap = {}

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        for page_idx in detail_page_indices:
            if page_idx < 0 or page_idx >= len(doc):
                continue
            page = doc[page_idx]
            textpage = page.get_textpage()
            full_text = textpage.get_text_range()

            # Find all (sheet, detail) pairs mentioned on this page
            seen_on_page: set[tuple[str, str]] = set()
            for m in HEADER_RE.finditer(full_text):
                sheet_id = m.group(1).upper()
                detail_num = m.group(2).upper()
                key = (detail_num, sheet_id)

                # Skip if already mapped (first occurrence wins)
                if key in detail_map:
                    continue
                if key in seen_on_page:
                    continue
                seen_on_page.add(key)

                # Locate the exact position via search
                occ = _search_header(textpage, sheet_id, detail_num)
                if occ is None:
                    continue

                char_start, length = occ
                bbox = _charboxes_union(textpage, char_start, length)

                detail_map[key] = DetailLocation(
                    page_index=page_idx,
                    bbox=bbox,
                    header_text=m.group(0).strip(),
                )
    finally:
        doc.close()

    return detail_map


def expand_bbox(
    bbox: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
    right_pts: float = 350.0,
    down_pts: float = 400.0,
) -> tuple[float, float, float, float]:
    """Expand a header bbox rightward and downward to capture the detail drawing.

    PDF coordinates: y=0 is at the bottom of the page, y increases upward.
    "Down" on screen = decreasing y in PDF space.

    Returns (x0, y0, x1, y1) clamped to page bounds.
    """
    x0, y0, x1, y1 = bbox
    # Expand: right (x increases) and down (y decreases in PDF space)
    new_x1 = min(x1 + right_pts, page_width)
    new_y0 = max(y0 - down_pts, 0.0)
    return (x0, new_y0, new_x1, y1)


def get_page_size(pdf_path: str | Path, page_index: int) -> tuple[float, float]:
    """Return (width, height) of a page in PDF points."""
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return doc[page_index].get_size()
    finally:
        doc.close()


def resolve_callouts(
    pdf_path: str | Path,
    callout_counts: dict,
    detail_page_indices: list[int],
) -> list[dict]:
    """Full stage-3 resolution: for each callout, find its detail location.

    callout_counts: output of callout.detect_callouts_text_layer()
      — dict keyed by (detail_num, sheet_id) → {count, typical, pages}

    Returns a list of resolution records:
      {
        "detail_num": str,
        "sheet_id": str,
        "callout_count": int,
        "typical": bool,
        "callout_pages": list[int],
        "detail_page_index": int | None,   # None = not found on detail pages
        "header_bbox": tuple | None,
        "crop_bbox": tuple | None,         # expanded for stage-4 extraction
        "resolved": bool,
      }
    Unresolved callouts (detail not found on any detail-sheet page) are included
    with resolved=False so the caller can log or fall back to vision on the whole page.
    """
    pdf_path = Path(pdf_path)
    detail_map = build_detail_map(pdf_path, detail_page_indices)

    # Pre-fetch page sizes for crop expansion (one per unique page)
    page_sizes: dict[int, tuple[float, float]] = {}
    for loc in detail_map.values():
        pi = loc["page_index"]
        if pi not in page_sizes:
            page_sizes[pi] = get_page_size(pdf_path, pi)

    records = []
    for (detail_num, sheet_id), info in callout_counts.items():
        loc = detail_map.get((detail_num, sheet_id))
        if loc:
            w, h = page_sizes[loc["page_index"]]
            crop = expand_bbox(loc["bbox"], w, h)
            records.append({
                "detail_num": detail_num,
                "sheet_id": sheet_id,
                "callout_count": info["count"],
                "typical": info["typical"],
                "callout_pages": info["pages"],
                "detail_page_index": loc["page_index"],
                "header_bbox": loc["bbox"],
                "crop_bbox": crop,
                "header_text": loc["header_text"],
                "resolved": True,
            })
        else:
            records.append({
                "detail_num": detail_num,
                "sheet_id": sheet_id,
                "callout_count": info["count"],
                "typical": info["typical"],
                "callout_pages": info["pages"],
                "detail_page_index": None,
                "header_bbox": None,
                "crop_bbox": None,
                "header_text": None,
                "resolved": False,
            })

    # Sort: resolved first, then by sheet_id + detail_num
    records.sort(key=lambda r: (not r["resolved"], r["sheet_id"], r["detail_num"]))
    return records
