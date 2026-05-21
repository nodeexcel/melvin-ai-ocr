"""
Run classification on all sample PDFs and write a summary report.
No API calls — text extraction + sheet number classification only.
"""
import re
import sys
import json
from pathlib import Path

import pypdfium2 as pdfium

PDFS = [
    "/home/lap-68/Downloads/2026-03-31_SVR_80% CD Set.pdf",
    "/home/lap-68/Downloads/2026-03-03 Whaleon Residence - CD Issue Set.pdf",
    "/home/lap-68/Downloads/2026_05-14 BARAGHOUSH DD progress.pdf",
    "/home/lap-68/Downloads/571 Paseo Miramar RTI Stamped Plans.pdf",
    "/home/lap-68/Downloads/4248 Woodlane Court - All Plans.pdf",
    "/home/lap-68/Downloads/2025_09-30 LHERT SONG CD Bid Set.pdf",
]

SHEET_NUMBER_MAP = {
    "S0":   "schedules",
    "S1":   None,
    "S2":   "framing_details",
    "T0-1": "schedules",
    "T0-2": "schedules",
    "T0-3": "schedules",
    "T0-6": "schedules",
    "A1":   "schedules",
    "A2":   "wall_framing",
    "HD":   "schedules",
    "F":    "foundation",
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


def extract_sheet_info(text):
    match = re.search(r'(?:^|[\r\n])([A-Z]{1,3}\d[\d.\-]*\d?)[\r\n]', text)
    if match:
        sheet_no = match.group(1).upper()
        before   = text[:match.start()].rstrip()
        last_nl  = before.rfind('\n')
        title    = before[last_nl + 1:].strip().lower()
        return sheet_no, title
    match2 = re.match(r'^([A-Z]{1,3}\d[\d.\-]*\d?)\s+(.+?)(?:\r\n|\n|$)', text.strip())
    if match2:
        return match2.group(1).upper(), match2.group(2).strip().lower()
    return "", ""


def classify(sheet_no, sheet_title):
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


def analyze_pdf(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        return {"error": "file not found", "name": path.name}

    doc        = pdfium.PdfDocument(str(path))
    total      = len(doc)
    pages      = []
    categories = {}

    for i in range(total):
        page     = doc[i]
        textpage = page.get_textpage()
        text     = textpage.get_text_range()
        textpage.close()
        page.close()

        sheet_no, title = extract_sheet_info(text)
        cat             = classify(sheet_no, title)
        pages.append({"page": i + 1, "sheet_no": sheet_no, "title": title[:50], "category": cat})
        categories[cat] = categories.get(cat, 0) + 1

    doc.close()

    relevant = [p for p in pages if p["category"] not in ("skip", "unknown")]
    has_s1   = any(p["sheet_no"].startswith("S1") for p in relevant)

    return {
        "name":       path.name,
        "size_mb":    round(path.stat().st_size / 1_000_000, 1),
        "total_pages": total,
        "categories": categories,
        "relevant_count": len(relevant),
        "has_s1_structural": has_s1,
        "relevant_pages": relevant,
    }


results = []
for pdf in PDFS:
    print(f"Analyzing: {Path(pdf).name} ...", flush=True)
    r = analyze_pdf(pdf)
    results.append(r)
    cats = r.get("categories", {})
    print(f"  {r.get('total_pages','?')} pages | relevant: {r.get('relevant_count','?')} | S1 sheets: {r.get('has_s1_structural','?')}")
    print(f"  {cats}")

with open("/tmp/all_pdfs_classification.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nDone → /tmp/all_pdfs_classification.json")
