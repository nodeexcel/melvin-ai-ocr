"""
PaddleOCR-based linear feet extraction from scanned structural PDF pages.
Requires PaddleOCR + PaddlePaddle — works on Python 3.11 (Docker base image).
Returns {} gracefully if PaddleOCR is unavailable.
"""
import re
import tempfile
from pathlib import Path

try:
    from paddleocr import PaddleOCR as _PaddleOCR
    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False

try:
    import fitz as _fitz
    _FITZ_AVAILABLE = True
except ImportError:
    _FITZ_AVAILABLE = False

from PIL import Image

TILE_SIZE = 2000
TILE_OVERLAP = 200
RENDER_SCALE = 1.5
DEDUP_DIST = 40

DIM_PATTERN = re.compile(
    r"[±~]?(\d{1,3})[''`][-\s]?(\d{1,2})[\"°*]?|[±~]?(\d{1,3})[''`](?!\d)"
)

EXCLUDE_KEYWORDS = {
    "cant", "cantilevered", "beam", "span", "header", "hdg",
    "clear", "elev", "elevation", "min.", "min ", "max.", "max ",
    "setback", "typ.", "typ ", "o.c.", "o.c", "@", "height",
}

_ocr_instance = None


def _get_ocr():
    global _ocr_instance, _PADDLE_AVAILABLE
    if _ocr_instance is None:
        try:
            _ocr_instance = _PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except Exception:
            _PADDLE_AVAILABLE = False
    return _ocr_instance


def _parse_ft(text: str) -> float | None:
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


def _is_footing_dim(text: str) -> bool:
    t_lower = text.lower()
    return not any(kw in t_lower for kw in EXCLUDE_KEYWORDS)


def _render_tiles(page, scale: float, tile_size: int, overlap: int):
    import fitz
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    full_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    w, h = full_img.size
    if w <= tile_size and h <= tile_size:
        return [(full_img, 0, 0)]
    tiles, step = [], tile_size - overlap
    y = 0
    while y < h:
        x = 0
        while x < w:
            x2, y2 = min(x + tile_size, w), min(y + tile_size, h)
            tiles.append((full_img.crop((x, y, x2, y2)), x, y))
            if x2 == w:
                break
            x += step
        if y2 == h:
            break
        y += step
    return tiles


def _ocr_tiles(ocr, tiles):
    items = []
    with tempfile.TemporaryDirectory() as tmp:
        for img, ox, oy in tiles:
            path = str(Path(tmp) / "tile.png")
            img.save(path)
            result = ocr.predict(path)
            if not result or not result[0].get("rec_texts"):
                continue
            for text, score, box in zip(
                result[0]["rec_texts"], result[0]["rec_scores"], result[0]["rec_boxes"]
            ):
                if score < 0.5 or not text.strip():
                    continue
                cx = (box[0] + box[2]) / 2 + ox
                cy = (box[1] + box[3]) / 2 + oy
                items.append({"text": text.strip(), "score": float(score), "cx": cx, "cy": cy})
    return items


def _dedup(items, dist):
    kept = []
    for item in items:
        dup = False
        for k in kept:
            if abs(item["cx"] - k["cx"]) < dist and abs(item["cy"] - k["cy"]) < dist:
                if item["score"] > k["score"]:
                    k.update(item)
                dup = True
                break
        if not dup:
            kept.append(item)
    return kept


# Known strap/connector patterns that appear as plan callouts
# Each occurrence on a plan = 1 piece installed at that location
_STRAP_PATTERNS = [
    (re.compile(r'CMSTC16', re.I), 'CMSTC16'),
    (re.compile(r'CMST14', re.I),  'CMST14'),
    (re.compile(r'CMST12', re.I),  'CMST12'),
    (re.compile(r'MST60',  re.I),  'MST60'),
    (re.compile(r'MST48',  re.I),  'MST48'),
    (re.compile(r'MST36',  re.I),  'MST36'),
    (re.compile(r'MSTC16', re.I),  'MSTC16'),
    (re.compile(r'CS14\b', re.I),  'CS14'),
    (re.compile(r'CS16\b', re.I),  'CS16'),
    (re.compile(r'LSTA24', re.I),  'LSTA24'),
    (re.compile(r'LSTA36', re.I),  'LSTA36'),
    (re.compile(r'ST6236', re.I),  'ST6236'),
    (re.compile(r'HDU\d+', re.I),  None),   # HDU2, HDU4, HDU8 etc — capture whole match
    (re.compile(r'HDUE\d+', re.I), None),
    (re.compile(r'PHD\d+', re.I),  None),
    (re.compile(r'SSTB\d+', re.I), None),
    (re.compile(r'A35\b', re.I),   'A35'),
    (re.compile(r'LTP4\b', re.I),  'LTP4'),
]
_CALLOUT_DEDUP_PX = 80  # two callouts within 80px = same location


def count_hardware_callouts(items: list[dict]) -> dict[str, int]:
    """
    Count hardware model callouts from OCR text items.
    Each unique occurrence on the plan = 1 piece at that location.
    Returns {model: count} — only models with count >= 1.
    """
    counts: dict[str, list[tuple]] = {}  # model → [(cx, cy), ...]

    for item in items:
        text = item['text']
        cx, cy = item['cx'], item['cy']

        for pattern, fixed_name in _STRAP_PATTERNS:
            m = pattern.search(text)
            if m:
                model = fixed_name if fixed_name else m.group(0).upper()
                if model not in counts:
                    counts[model] = []
                # Deduplicate: skip if we already have a callout within DEDUP px
                is_dup = any(
                    abs(cx - ex) < _CALLOUT_DEDUP_PX and abs(cy - ey) < _CALLOUT_DEDUP_PX
                    for ex, ey in counts[model]
                )
                if not is_dup:
                    counts[model].append((cx, cy))

    return {m: len(locs) for m, locs in counts.items() if locs}


def extract_lf_from_pages(pdf_path: str, page_indices: list[int]) -> dict:
    """
    Run PaddleOCR on the given page indices (0-indexed) and return LF data.
    Returns {} if PaddleOCR or fitz are not available.
    """
    if not _PADDLE_AVAILABLE or not _FITZ_AVAILABLE:
        return {}

    import fitz
    doc = fitz.open(pdf_path)
    ocr = _get_ocr()
    if ocr is None:
        return {}

    pages_out = []
    for idx in page_indices:
        page = doc[idx]
        tiles = _render_tiles(page, RENDER_SCALE, TILE_SIZE, TILE_OVERLAP)
        items = _dedup(_ocr_tiles(ocr, tiles), DEDUP_DIST)

        drawing_scale = ""
        for item in items:
            if re.search(r"1/4[°*\"']?\s*=\s*1", item["text"], re.IGNORECASE):
                drawing_scale = item["text"].strip()
                break

        dimensions = []
        for item in items:
            val = _parse_ft(item["text"])
            if val is not None:
                dimensions.append({
                    "text": item["text"],
                    "feet": round(val, 2),
                    "likely_footing": _is_footing_dim(item["text"]),
                })

        footing_lf = sum(d["feet"] for d in dimensions if d["likely_footing"])
        hw_callouts = count_hardware_callouts(items)
        pages_out.append({
            "page": idx + 1,
            "drawing_scale": drawing_scale,
            "total_lf": round(footing_lf, 1),
            "dimensions": dimensions,
            "hardware_callouts": hw_callouts,
        })

    # Aggregate hardware counts across all pages
    total_hardware: dict[str, int] = {}
    for p in pages_out:
        for model, count in p.get("hardware_callouts", {}).items():
            total_hardware[model] = total_hardware.get(model, 0) + count

    return {
        "pages": pages_out,
        "grand_total_lf": round(sum(p["total_lf"] for p in pages_out), 1),
        "hardware_counts": total_hardware,
    }
