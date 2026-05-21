import re

SHEET_NUMBER_MAP: dict[str, str | None] = {
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
    "S-1":  "schedules",
    "S-2":  None,
    "T1":   "framing_details",
    "S-3":  "framing_details",
    "S-4":  "framing_details",
}

S1_TITLE_MAP: dict[str, str] = {
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

TEXT_HEAVY_MIN_CHARS = 2000
VISION_ONLY_CATEGORIES = {"floor_framing", "roof_framing", "foundation"}


def extract_sheet_info(text: str) -> tuple[str, str]:
    """Return (sheet_no, sheet_title) from title block text. Empty strings if not found."""
    # Pattern 5: Ashley & Vance — "AV JOB:" marker
    if "AV JOB:" in text:
        m = re.search(r"AV JOB:\r?\n((?:[^\n\r]*\r?\n){1,4})(S-\d[\d.]*)", text)
        if m:
            title = m.group(1).replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
            return m.group(2).upper(), title.lower()

    # Pattern 3: Aram Ark / Whaleon — "A.A. S-2.0 SCALE TITLE" near end
    m3 = re.search(r"A\.A\.\s+([A-Z]{1,2}-\d[\d\.]*)(. +?)$", text, re.MULTILINE)
    if m3:
        title_m = re.search(r"([A-Z][A-Z ]{3,})\s*$", m3.group(2))
        if title_m:
            return m3.group(1).upper(), title_m.group(1).strip().lower()

    # Pattern 4: BARAGHOUSH — sheet# before "REVISION CLOUD SCHEDULE"
    m4 = re.search(r"([A-Z]{1,2}-\d[\d\.]*)\s+REVISION CLOUD SCHEDULE", text)
    if m4:
        sheet_no = m4.group(1).upper()
        scale_m = re.search(r"SCALE:\s*[^\n\r]+\s+([A-Z][A-Z ]+?)(?:\s+\d+\s*$|\s*$)", text, re.MULTILINE)
        title = scale_m.group(1).strip().lower() if scale_m else ""
        return sheet_no, title

    # Pattern 1: sheet number on its own line (BSPK / Zahn)
    m1 = re.search(r"(?:^|[\r\n])([A-Z]{1,3}\d[\d.\-]*\d?)[\r\n]", text)
    if m1:
        sheet_no = m1.group(1).upper()
        before = text[: m1.start()].rstrip()
        last_nl = before.rfind("\n")
        title = before[last_nl + 1 :].strip().lower()
        return sheet_no, title

    # Pattern 2: sheet number at start of text (landscape/civil)
    m2 = re.match(r"^([A-Z]{1,3}\d[\d.\-]*\d?)\s+(.+?)(?:\r\n|\n|$)", text.strip())
    if m2:
        return m2.group(1).upper(), m2.group(2).strip().lower()

    return "", ""


def classify_page(text: str) -> str:
    """Return category string for a page based on its sheet number."""
    sheet_no, sheet_title = extract_sheet_info(text)

    if not sheet_no:
        return "unknown"

    if any(sheet_no.startswith(p) for p in SKIP_PREFIXES):
        return "skip"

    if sheet_no.startswith("S1") or sheet_no.startswith("S-2"):
        for kw, cat in S1_TITLE_MAP.items():
            if kw in sheet_title:
                return cat
        return "framing_details"

    for prefix in sorted(SHEET_NUMBER_MAP.keys(), key=len, reverse=True):
        if sheet_no.startswith(prefix):
            result = SHEET_NUMBER_MAP[prefix]
            return result if result else "unknown"

    return "unknown"


def is_text_heavy(text: str, category: str) -> bool:
    """True when the page should use text extraction instead of Vision."""
    if category in VISION_ONLY_CATEGORIES:
        return False
    if category == "schedules" and len(text.strip()) > 100:
        return True
    return len(text.strip()) > TEXT_HEAVY_MIN_CHARS
