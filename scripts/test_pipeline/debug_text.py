"""Print raw text from key pages to understand pypdfium2 text ordering."""
import pypdfium2 as pdfium

PDF_PATH = '/home/lap-68/Downloads/2026-03-31_SVR_80% CD Set.pdf'

doc = pdfium.PdfDocument(PDF_PATH)

# Check pages 1, 11, 12, 50 (we know 11 is T0-400, 12 is T0-500 from earlier)
for i in [0, 10, 11, 49]:
    page     = doc[i]
    textpage = page.get_textpage()
    text     = textpage.get_text_range()
    print(f"\n{'='*60}")
    print(f"PAGE {i+1} — last 600 chars:")
    print(repr(text[-600:]))
    textpage.close()
    page.close()

doc.close()

with open('/tmp/debug_text.txt', 'w') as f:
    doc2 = pdfium.PdfDocument(PDF_PATH)
    for i in [0, 10, 11, 49]:
        page     = doc2[i]
        textpage = page.get_textpage()
        text     = textpage.get_text_range()
        f.write(f"\n{'='*60}\nPAGE {i+1}:\n{text}\n")
        textpage.close()
        page.close()
    doc2.close()

print("\nFull text written to /tmp/debug_text.txt")
