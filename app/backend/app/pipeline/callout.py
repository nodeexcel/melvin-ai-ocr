"""Text-layer detail-callout detector — stage 2 of the callout engine.

Detects circle-callout markers in the text layer of CAD-exported PDFs.
Each callout references a specific detail on a specific detail sheet:
  e.g.  SD2 / 7A   →   detail "7A" on sheet "SD2"

Returns per-pair counts that drive the rollup in stage 5:
  hardware-per-detail  ×  callout-count  →  total hardware quantity

Stage 2 of the 5-stage callout engine.
See docs/analysis-2026-06-20/08-detail-callout-engine-design.md.

Design rules (from spike on 8603 Rugby / Terra Nova format):
  • Key on the FULL (detail_num, sheet_id) pair — numbers restart per sheet.
  • Text-layer PDFs store callout markers as adjacent text objects:
      SDx   then   num          (two consecutive tokens)
      SDx num      [inline]     (single token, space-separated)
  • The detail-number token may have trailing annotation text:
      "4 2x12 F.J. @ 16\" O.C."  →  detail "4"  (extra = structural note)
  • TYP. suffix means the detail applies throughout; keep the marker count
    as-is and flag it — the estimator adjusts the multiplier.
  • Run ONLY on plan pages (foundation, framing, wall).  Passing detail-sheet
    page indices will inflate counts with detail-box headers.  The caller
    is responsible for filtering by page category (classify.py output).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

import pypdfium2 as pdfium

# ── Token patterns ─────────────────────────────────────────────────────────────

# Sheet ID: SD1 SD2 SD3 SD4 S4 (Locke format, raster — unlikely in text layer
# but harmless to accept); D1 / D-1 excluded — too broad, collides with
# dimension annotations like "D-4" or downfall tag "D2".
_SHEET_RE = re.compile(r"^(SD\d+[A-Z]?|S\d+[A-Z]?)$", re.IGNORECASE)

# Detail number at the START of a token.
# Accepts:   "1"  "7A"  "20"  "4 2x12 F.J."  "16 TYP."
# Rejects:   "4x4 POST"  "2x12"  "3 L=14'"  "TYP." alone
#   — \d+    one-or-more digits
#   — [A-Z]? optional single suffix letter (7A, 8B…)
#   — \b      word boundary (blocks "4x4", "2x12")
_DETAIL_PREFIX_RE = re.compile(r"^(\d+[A-Z]?)\b\s*(TYP\.?)?", re.IGNORECASE)

# Inline single-token: "SD2 7A"  "SD2 7A TYP."
_INLINE_RE = re.compile(
    r"^(SD\d+[A-Z]?|S\d+[A-Z]?)\s+(\d+[A-Z]?)\b\s*(TYP\.?)?",
    re.IGNORECASE,
)


# ── Public types ───────────────────────────────────────────────────────────────

class CalloutInfo(TypedDict):
    count: int          # number of callout markers found on the plan pages
    typical: bool       # at least one marker was labeled "TYP." (applies throughout)
    pages: list[int]    # 1-based page numbers where callouts appear


CalloutCounts = dict[tuple[str, str], CalloutInfo]   # key: (detail_num, sheet_id)


# ── Core detection ─────────────────────────────────────────────────────────────

def _extract_tokens(text: str) -> list[str]:
    """Split PDF text into non-empty fragments, preserving text-object order."""
    return [t.strip() for t in re.split(r"[\n\r]+", text) if t.strip()]


def _scan_tokens(tokens: list[str], page_num: int, counts: dict) -> None:
    """Scan one page's token list and update counts in place."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # Check inline format first: "SD2 7A [TYP.]"
        m = _INLINE_RE.match(tok)
        if m:
            _record(counts, m.group(2).upper(), m.group(1).upper(), bool(m.group(3)), page_num)
            i += 1
            continue

        # Check for sheet-ID token followed by a detail-number token
        if _SHEET_RE.match(tok):
            sheet_id = tok.upper()
            if i + 1 < len(tokens):
                m2 = _DETAIL_PREFIX_RE.match(tokens[i + 1])
                if m2:
                    _record(counts, m2.group(1).upper(), sheet_id, bool(m2.group(2)), page_num)
                    i += 2
                    continue

        i += 1


def _record(counts: dict, detail_num: str, sheet_id: str, typical: bool, page_num: int) -> None:
    key = (detail_num, sheet_id)
    info = counts[key]
    info["count"] += 1
    info["typical"] = info["typical"] or typical
    if page_num not in info["pages"]:
        info["pages"].append(page_num)


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_callouts_text_layer(
    pdf_path: str | Path,
    page_indices: list[int],
) -> CalloutCounts:
    """Detect and count detail callouts on the given plan pages (0-based indices).

    Only reads the PDF text layer — no LLM, no OCR, no API calls.
    Pass only plan-page indices (not detail-sheet or schedule pages).

    Returns a dict keyed by (detail_num, sheet_id) → CalloutInfo.
    Returns {} if no callouts found or the PDF has no text layer.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    # defaultdict produces CalloutInfo-shaped dicts automatically
    counts: dict = defaultdict(lambda: {"count": 0, "typical": False, "pages": []})

    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        for idx in page_indices:
            if idx < 0 or idx >= len(doc):
                continue
            page = doc[idx]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            tokens = _extract_tokens(text)
            _scan_tokens(tokens, idx + 1, counts)   # page numbers are 1-based
    finally:
        doc.close()

    return dict(counts)


def has_text_layer(pdf_path: str | Path, page_index: int, min_chars: int = 200) -> bool:
    """Return True if the given page (0-based) has a substantial text layer.

    Used by the multi-modal dispatcher to choose text-layer vs vision/OCR path.
    min_chars=200 mirrors classify.py's TEXT_HEAVY_MIN_CHARS intent while being
    tuned for structural plan pages (which are text-sparse even in CAD exports).
    """
    pdf_path = Path(pdf_path)
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        if page_index < 0 or page_index >= len(doc):
            return False
        page = doc[page_index]
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        return len(text.strip()) >= min_chars
    finally:
        doc.close()


def summarise_callouts(counts: CalloutCounts) -> dict:
    """Return a human-readable summary dict for logging / progress messages.

    Structure:
      {
        "total_markers": int,
        "unique_pairs": int,
        "by_sheet": {"SD1": 22, "SD2": 19, ...},
        "typical_pairs": [("5", "SD1"), ...],
      }
    """
    total = sum(v["count"] for v in counts.values())
    by_sheet: dict[str, int] = defaultdict(int)
    typical_pairs: list[tuple[str, str]] = []
    for (det, sheet), info in counts.items():
        by_sheet[sheet] += info["count"]
        if info["typical"]:
            typical_pairs.append((det, sheet))
    return {
        "total_markers": total,
        "unique_pairs": len(counts),
        "by_sheet": dict(by_sheet),
        "typical_pairs": sorted(typical_pairs),
    }
