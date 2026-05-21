"""
Quick classification test using pypdfium2 (fast, low memory).
Tests sheet number extraction and category mapping without API calls.
"""
import re
import sys
sys.path.insert(0, '/home/lap-68/Documents/gt-atul/atul-melvin-architecture-analysis-and-analysis/scripts/test_pipeline')

import pypdfium2 as pdfium

PDF_PATH = '/home/lap-68/Downloads/2026-03-31_SVR_80% CD Set.pdf'
MAX_PAGES = 167

# ---------------------------------------------------------------------------
# Same classification logic as test_pipeline.py (duplicated for standalone run)
# ---------------------------------------------------------------------------

SHEET_NUMBER_MAP = {
    "S0":   "schedules",
    "S1":   None,              # further classified by title
    "S2":   "framing_details",
    "T0-1": "schedules",
    "T0-2": "schedules",
    "T0-3": "schedules",
    "A1":   "schedules",
    "A2":   "wall_framing",
}

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

SKIP_PREFIXES = ("L", "M", "E", "P", "C", "A3", "A4", "A5", "A6", "T0-4", "T0-5")

# T0-6xx: door/window schedules — useful for header rough openings
SHEET_NUMBER_MAP["T0-6"] = "schedules"
# HDU, F pages — Simpson hold-down schedules, relevant
SHEET_NUMBER_MAP["HD"]  = "schedules"
SHEET_NUMBER_MAP["F"]   = "foundation"


def extract_sheet_info(text: str):
    # Pattern 1: sheet number on its own line (BSPK title block format)
    # e.g. "CITY DOCUMENTS\r\nT0-400\r\n"
    match = re.search(r'(?:^|[\r\n])([A-Z]{1,3}\d[\d.\-]*\d?)[\r\n]', text)
    if match:
        sheet_no = match.group(1).upper()
        # Title is the last non-empty line before the sheet number
        before = text[:match.start()].rstrip()
        last_nl = before.rfind('\n')
        sheet_title = before[last_nl + 1:].strip().lower()
        return sheet_no, sheet_title

    # Pattern 2: sheet number at start of text (landscape/civil title block format)
    # e.g. "L0.1 GENERAL NOTES ..." or "L4.0 HARDSCAPE DETAILS ..."
    match2 = re.match(r'^([A-Z]{1,3}\d[\d.\-]*\d?)\s+(.+?)(?:\r\n|\n|$)', text.strip())
    if match2:
        sheet_no = match2.group(1).upper()
        sheet_title = match2.group(2).strip().lower()
        return sheet_no, sheet_title

    return "", ""


def classify(sheet_no: str, sheet_title: str) -> str:
    if not sheet_no:
        return "unknown"
    if any(sheet_no.startswith(p) for p in SKIP_PREFIXES):
        return "skip"
    if sheet_no.startswith("S1"):
        for kw, cat in S1_TITLE_MAP.items():
            if kw in sheet_title:
                return cat
        return "framing_details"
    for prefix in sorted(SHEET_NUMBER_MAP.keys(), key=len, reverse=True):
        if sheet_no.startswith(prefix):
            result = SHEET_NUMBER_MAP[prefix]
            return result if result else "unknown"
    return "unknown"


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

doc = pdfium.PdfDocument(PDF_PATH)
total = min(len(doc), MAX_PAGES)

results = []
for i in range(total):
    page     = doc[i]
    textpage = page.get_textpage()
    text     = textpage.get_text_range()
    sheet_no, title = extract_sheet_info(text)
    cat = classify(sheet_no, title)
    results.append((i + 1, sheet_no, title[:40], cat))
    textpage.close()
    page.close()

doc.close()

# Write to file
with open('/tmp/classify_test.txt', 'w') as f:
    for page_num, no, title, cat in results:
        f.write(f'{page_num:3d}  {no:12s}  {title:40s}  {cat}\n')

print(f"Done. Wrote {len(results)} pages to /tmp/classify_test.txt")
