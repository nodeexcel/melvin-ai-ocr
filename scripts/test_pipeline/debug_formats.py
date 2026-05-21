"""Check title block format of pages from each unknown PDF."""
import pypdfium2 as pdfium
from pathlib import Path

PDFS = [
    "/home/lap-68/Downloads/2026-03-03 Whaleon Residence - CD Issue Set.pdf",
    "/home/lap-68/Downloads/2026_05-14 BARAGHOUSH DD progress.pdf",
    "/home/lap-68/Downloads/571 Paseo Miramar RTI Stamped Plans.pdf",
    "/home/lap-68/Downloads/4248 Woodlane Court - All Plans.pdf",
    "/home/lap-68/Downloads/2025_09-30 LHERT SONG CD Bid Set.pdf",
]

with open("/tmp/format_debug.txt", "w") as f:
    for pdf_path in PDFS:
        path = Path(pdf_path)
        doc  = pdfium.PdfDocument(str(path))
        f.write(f"\n{'='*60}\n{path.name} ({len(doc)} pages)\n{'='*60}\n")

        # Sample pages 1, 2, 3 and last 300 chars of each
        for i in [0, 1, 2]:
            if i >= len(doc):
                continue
            page     = doc[i]
            textpage = page.get_textpage()
            text     = textpage.get_text_range()
            textpage.close()
            page.close()
            f.write(f"\n--- Page {i+1} (first 400) ---\n{text[:400]}\n")
            f.write(f"--- Page {i+1} (last 300) ---\n{text[-300:]}\n")

        doc.close()

print("Done → /tmp/format_debug.txt")
