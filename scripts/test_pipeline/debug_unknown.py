"""Check raw text on unknown pages 20-49 to find missing S1 sheets."""
import pypdfium2 as pdfium

PDF_PATH = '/home/lap-68/Downloads/2026-03-31_SVR_80% CD Set.pdf'
doc = pdfium.PdfDocument(PDF_PATH)

with open('/tmp/unknown_pages.txt', 'w') as f:
    for i in range(19, 50):  # pages 20-50
        page     = doc[i]
        textpage = page.get_textpage()
        text     = textpage.get_text_range()
        f.write(f"\n{'='*50}\nPAGE {i+1}:\n{text[:500]}\n...\n{text[-300:]}\n")
        textpage.close()
        page.close()

doc.close()
print("Done → /tmp/unknown_pages.txt")
