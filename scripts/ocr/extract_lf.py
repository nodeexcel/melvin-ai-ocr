#!/usr/bin/env python3
"""
Extract linear feet from scanned structural PDF pages using PaddleOCR.

Requires Python 3.11 + PaddleOCR 3.3.0 + PaddlePaddle 3.2.0.
Run from repo root: source venv/melvin311/bin/activate

Usage:
  python scripts/ocr/extract_lf.py --pdf /path/to/file.pdf --pages 35,36,37
  python scripts/ocr/extract_lf.py --pdf /path/to/file.pdf --pages 35 --debug
"""

import argparse
import json
import re
import sys
from pathlib import Path

import fitz
from paddleocr import PaddleOCR
from PIL import Image

TILE_SIZE = 2000
TILE_OVERLAP = 200
RENDER_SCALE = 1.5
DEDUP_DIST = 40  # pixels — text items within this distance treated as same

# Regex for feet-inches: 14'-0", 28'-6", ±8'-6", ~3'-3", 10'-11", 15'
DIM_PATTERN = re.compile(r"[±~]?(\d{1,3})[''`][-\s]?(\d{1,2})[\"°*]?|[±~]?(\d{1,3})[''`](?!\d)")

# Strings that indicate a dimension is NOT a footing run (exclude from LF sum)
EXCLUDE_KEYWORDS = {"cant", "cantilevered", "beam", "span", "header", "hdg", "clear", "elev", "elevation"}


def _parse_ft(text: str) -> float | None:
    """Parse a feet-inches string to decimal feet. Returns None if not parseable."""
    m = DIM_PATTERN.match(text.strip())
    if not m:
        return None
    if m.group(1) and m.group(2):
        val = int(m.group(1)) + int(m.group(2)) / 12
    elif m.group(3):
        val = float(m.group(3))
    else:
        return None
    return val if 1.0 < val < 250 else None


def _is_footing_dim(text: str, context: list[str]) -> bool:
    """Heuristic: is this dimension likely a footing run rather than a beam span/other?"""
    t_lower = text.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in t_lower:
            return False
    return True


def _render_tiles(page, scale: float, tile_size: int, overlap: int) -> list[tuple[Image.Image, int, int]]:
    """Render a page and split into overlapping tiles. Returns list of (image, x_offset, y_offset)."""
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    full_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = full_img.size

    if w <= tile_size and h <= tile_size:
        return [(full_img, 0, 0)]

    tiles = []
    step = tile_size - overlap
    y = 0
    while y < h:
        x = 0
        while x < w:
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            tile = full_img.crop((x, y, x2, y2))
            tiles.append((tile, x, y))
            if x2 == w:
                break
            x += step
        if y2 == h:
            break
        y += step

    return tiles


def _ocr_tiles(ocr: PaddleOCR, tiles: list[tuple[Image.Image, int, int]]) -> list[dict]:
    """Run OCR on each tile, return items with global coordinates."""
    all_items = []
    for img, ox, oy in tiles:
        tmp = "/tmp/_ocr_tile.png"
        img.save(tmp)
        result = ocr.predict(tmp)
        if not result or not result[0].get("rec_texts"):
            continue
        texts = result[0]["rec_texts"]
        scores = result[0]["rec_scores"]
        boxes = result[0]["rec_boxes"]  # [x1, y1, x2, y2]
        for text, score, box in zip(texts, scores, boxes):
            if score < 0.5 or not text.strip():
                continue
            cx = (box[0] + box[2]) / 2 + ox
            cy = (box[1] + box[3]) / 2 + oy
            all_items.append({"text": text.strip(), "score": round(float(score), 3), "cx": cx, "cy": cy})
    return all_items


def _dedup(items: list[dict], dist: int) -> list[dict]:
    """Remove duplicate text items that overlap between tiles."""
    kept = []
    for item in items:
        duplicate = False
        for k in kept:
            if abs(item["cx"] - k["cx"]) < dist and abs(item["cy"] - k["cy"]) < dist:
                # Keep higher confidence
                if item["score"] > k["score"]:
                    k.update(item)
                duplicate = True
                break
        if not duplicate:
            kept.append(item)
    return kept


def extract_page(ocr: PaddleOCR, pdf_path: str, page_index: int, debug: bool = False) -> dict:
    """Extract LF and dimensions from a single page."""
    doc = fitz.open(pdf_path)
    page = doc[page_index]

    tiles = _render_tiles(page, RENDER_SCALE, TILE_SIZE, TILE_OVERLAP)
    items = _ocr_tiles(ocr, tiles)
    items = _dedup(items, DEDUP_DIST)

    if debug:
        print(f"\n  Total unique text items: {len(items)}")

    # Extract scale
    drawing_scale = ""
    for item in items:
        t = item["text"]
        if re.search(r"1/4[°*\"']?\s*=\s*1", t, re.IGNORECASE) or re.search(r"scale.*1.*0", t, re.IGNORECASE):
            drawing_scale = t.strip()
            break

    # Extract all dimension callouts
    all_texts = [it["text"] for it in items]
    dimensions = []
    for item in items:
        t = item["text"]
        val = _parse_ft(t)
        if val is not None:
            is_footing = _is_footing_dim(t, all_texts)
            dimensions.append({
                "text": t,
                "feet": round(val, 2),
                "likely_footing": is_footing,
                "cx": round(item["cx"]),
                "cy": round(item["cy"]),
            })

    footing_dims = [d for d in dimensions if d["likely_footing"]]
    total_lf = round(sum(d["feet"] for d in footing_dims), 1)

    if debug:
        print(f"  Drawing scale: {drawing_scale!r}")
        print(f"  All dimensions ({len(dimensions)}):")
        for d in sorted(dimensions, key=lambda x: -x["feet"]):
            flag = "FOOTING" if d["likely_footing"] else "skip"
            print(f"    {d['text']:<25} = {d['feet']:.1f} ft  [{flag}]")
        print(f"  Total footing LF estimate: {total_lf} ft")

    return {
        "page": page_index + 1,
        "drawing_scale": drawing_scale,
        "total_lf": total_lf,
        "dimensions": dimensions,
        "tile_count": len(tiles),
        "text_count": len(items),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract linear feet from scanned structural PDF pages")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--pages", required=True, help="Comma-separated 1-indexed page numbers, e.g. 35,36,37")
    parser.add_argument("--debug", action="store_true", help="Print detailed extraction info")
    parser.add_argument("--out", default=None, help="Output JSON path (default: stdout)")
    args = parser.parse_args()

    pdf_path = args.pdf
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    page_nums = [int(p.strip()) for p in args.pages.split(",")]

    print("Initialising PaddleOCR...", file=sys.stderr)
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )

    results = []
    for p in page_nums:
        print(f"Processing page {p}...", file=sys.stderr)
        result = extract_page(ocr, pdf_path, p - 1, debug=args.debug)
        results.append(result)
        print(f"  p{p}: {result['total_lf']} LF from {len(result['dimensions'])} dimensions ({result['tile_count']} tiles, {result['text_count']} text items)", file=sys.stderr)

    summary = {
        "pdf": pdf_path,
        "pages": results,
        "grand_total_lf": round(sum(r["total_lf"] for r in results), 1),
    }

    output = json.dumps(summary, indent=2)
    if args.out:
        Path(args.out).write_text(output)
        print(f"Saved to {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
