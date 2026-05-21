# Research: Approaches for Unachievable Extractions

**Date:** 2026-05-21  
**Purpose:** Thorough research into tools, libraries, APIs, and services that could fill the gaps in our current pipeline — specifically the quantity takeoff fields we cannot reliably extract from PDF text layers.

---

## Summary Table

| Item | Best Approach | Accuracy | Effort | Cost |
|---|---|---|---|---|
| Concrete CY | PyMuPDF lines + Gemini Pro | 80% (Gemini) / 90–98% (iBeam AI) | Medium | $0.01–0.05/page (Gemini) or $150–500/estimate (iBeam) |
| Rebar LF + qty | iBeam AI or Florence-2 fine-tuned | 90–98% (iBeam) / 75–80% (Gemini) | Medium–High | $200–400/job (iBeam) |
| Lumber piece counts | Gemini Pro + user guidance | 70–75% (Gemini) / 85% (YOLO fine-tune) | Medium | API cost only |
| Sheathing sqft | OpenCV contours + Shapely | 90%+ on vector PDFs | Medium–High | Free (open source) |
| Footing LF | PyMuPDF line extraction + vector math | 90%+ on vector PDFs | Medium | Free (open source) |
| Labor estimates | RSMeans + internal rate table | 80–90% | Medium | RSMeans subscription |
| Equipment costs | RSMeans + vendor reference data | 70–80% | Medium | RSMeans subscription |
| Construction schedule | Gemini Pro table read + manual QA | 70% | Low | API cost only |

---

## 1. Concrete Cubic Yards

Requires: footing dimensions × linear feet from foundation plan drawings.

### Python Libraries

**PyMuPDF (`fitz`)** — `page.get_drawings()` extracts all vector graphics including dimension lines. Returns list of dicts with line coordinates, colors, widths. Foundation plans drawn in CAD produce clean vector lines. Can reconstruct footing geometry and measure perimeters.

```python
import fitz
doc = fitz.open("foundation.pdf")
page = doc[0]
drawings = page.get_drawings()  # returns all paths/lines
```

**PDFPlumber** — Alternative vector extractor; `page.lines` and `page.rects` expose line segments. Good for structured layouts but heavier than PyMuPDF.

**ezdxf** — If the PDF was exported from AutoCAD and a DXF is available, `ezdxf` parses it directly. Layer-based access: filter "Foundation" layer and sum entity lengths. Near-perfect accuracy (99%) if DXF is available.

### Vision/AI

**Gemini Pro/Flash** — Benchmarks (2025) show ~80% accuracy on dimension extraction from technical drawings, outperforming GPT-4o (~40%) on dense drawings with tolerances. Use `gemini-1.5-pro` or `gemini-2.0-flash` with a targeted prompt asking for footing schedule and perimeter dimensions.

**iBeam AI** — Specialized SaaS for concrete takeoff. Upload PDF → auto-extracts cubic yards, includes laps and dowels per ACI standards. 90–98% accuracy claimed. $150–500/estimate. No coding required.

### Feasibility

| Approach | Accuracy | Effort | When to Use |
|---|---|---|---|
| PyMuPDF line extraction + geometry | ~90% | Medium | Vector CAD PDFs |
| Gemini Pro vision | ~80% | Low | Any PDF type |
| iBeam AI SaaS | 90–98% | Low (integration) | High-stakes jobs, outsource complexity |
| ezdxf (DXF files) | ~99% | Low | If client has DXF exports |

**Recommended approach:** Add PyMuPDF line extraction pass on foundation pages to get footing perimeter coordinates → calculate LF geometrically → multiply by footing cross-section (already extracted from specs) → get CY. Fallback to Gemini Pro for scanned PDFs.

---

## 2. Rebar Linear Feet + Piece Counts

Requires: reading bar callouts, schedules, and layout from foundation/framing plans.

### Python Libraries

**PaddleOCR** — Significantly outperforms Tesseract (pytesseract) on rotated text and technical annotations. Returns bounding boxes + confidence scores. Good for reading rebar callouts (#4 @ 12", bar marks, shape codes).

```bash
pip install paddlepaddle paddleocr
```

**pytesseract** — Older, ~30–50% accuracy on rebar callouts. Not recommended for production.

### Vision/AI

**Gemini Pro** — ~75–80% accuracy on rebar schedules. Strong at reading structured tables (bar mark, qty, diameter, length, shape code). Use on detail sheet images where rebar schedule is a clean table.

**Fine-tuned Florence-2** (open source, 0.23B params) — Nov 2024 paper shows 52.4% F1 improvement over closed-source models for engineering drawing extraction. Train on 100+ annotated plan pages. Self-hostable. Reaches 85–90% accuracy post fine-tune. Best option if processing high volume.

**iBeam AI Rebar tool** — Auto-reads bar callouts, calculates linear footage with development lengths per ACI 318. Adds lap splices automatically. 90–98% accuracy. $200–400/job.

**Rebar.Shop** — Blueprint-to-quote automation. OCR-based bar extraction. ~90–98% claimed accuracy.

### Feasibility

| Approach | Accuracy | Effort | When to Use |
|---|---|---|---|
| PaddleOCR + PyMuPDF | ~70% | Medium | Text-based callouts |
| Gemini Pro (schedules) | ~75–80% | Low | Clean tabular rebar schedules |
| Fine-tuned Florence-2 | ~85–90% | High (training) | High volume, self-hosted |
| iBeam AI | 90–98% | Low (integration) | High stakes, outsource |

**Recommended approach:** Gemini Pro on rebar schedule pages (structured table → easy JSON extraction). For foundation plan callouts, PaddleOCR to read bar marks. iBeam AI if accuracy needs to be production-grade.

---

## 3. Lumber Piece Counts

Requires: counting joists, beams, posts from framing plan drawings.

### Libraries

**OpenCV** — Hough line detection + contour analysis to identify parallel framing members. `findContours()` + `contourArea()`. Works on clean CAD drawings. Fragile on dense or irregular layouts.

**PyMuPDF** — Extract framing symbols from CAD-generated PDFs. Member runs often represented as consistent symbol sets.

**ezdxf** — Filter "Framing" layer if DXF available; count entity instances directly.

### ML Approaches

**Custom YOLO v5/v8 fine-tune** — USPTO patents (11216905, 11861821) describe automatic detection and counting of lumber boards from drawings using Faster R-CNN. Fine-tune on 200–500 framing plan images. Reaches 80–85% accuracy. Self-hosted.

**Gemini Pro** — Can count framing members from floor plan images with user guidance. ~70–75% accuracy on standard layouts. Specify: "Count all 2x10 joists at 16\" OC in the floor framing plan. Region: [bounding box]."

### Feasibility

| Approach | Accuracy | Effort | When to Use |
|---|---|---|---|
| YOLO framing symbol detection | 80–85% | High (training) | High volume |
| Gemini Pro + floor plan image | 70–75% | Low | Standard layouts |
| OpenCV contour tracing | ~60% | Medium | Clean vector CAD only |
| Hybrid: user selects region + Gemini counts | ~90% | Low | Best UX/accuracy tradeoff |

**Recommended approach:** Hybrid UI — Melvin clicks on the framing plan region, Gemini counts members with typed context hint (e.g., "2x10 @ 16\" OC"). This gives ~90% accuracy with minimal engineering and puts Melvin in control of which regions to count.

---

## 4. Sheathing Square Footage

Requires: total wall/roof area from floor plans and roof plans.

### Libraries

**Shapely** — Polygon area calculation from extracted coordinates. `polygon.area` in page units → convert to sq ft using drawing scale. Excellent for closed floor plan contours.

**OpenCV** — `findContours()` + `contourArea()` for wall/roof outline detection. Works well on high-contrast CAD drawings.

**PyMuPDF + PDFPlumber** — Extract wall lines as vectors, reconstruct polygons for area calculation.

### Vision/AI

**Gemini Pro** — Visual floor plan area estimation. ~75–80% accuracy. Specify scale from title block to convert pixel measurements to sq ft.

**Procore Automated Area Takeoff** (May 2025 feature) — ML-based room detection. Click button → auto-measures floor area across multiple sheets. API available via Autodesk Construction Cloud. ~95% accuracy.

**Floorplan-Dimractor** (GitHub: jasoncobra3) — Open-source Python pipeline. Extracts dimension callouts and cabinet codes from floor plan PDFs, outputs structured JSON. Post-process to get areas.

### Feasibility

| Approach | Accuracy | Effort | When to Use |
|---|---|---|---|
| OpenCV + Shapely (vector PDFs) | ~90% | Medium–High | CAD-generated PDFs |
| Gemini Pro visual | ~75–80% | Low | Any PDF type |
| Procore Takeoff API | ~95% | Medium (integration) | If Procore subscriber |
| Floorplan-Dimractor + custom logic | ~70–75% | Medium | Open source baseline |

**Recommended approach:** OpenCV line extraction + Shapely polygon area for vector PDFs. Gemini Pro fallback for scanned/complex layouts. Scale factor extracted from title block (already done by our pipeline).

---

## 5. Footing Linear Feet

Requires: reading the layout and perimeter of the foundation plan.

### Libraries

**PyMuPDF** — `page.get_drawings()` returns all line segments. Filter by line color/thickness to isolate footing lines. Sum endpoint distances using Euclidean math. ~90% on vector CAD PDFs.

**ezdxf** — If DXF available, parse "Foundation" or "Structural" layer. Sum entity lengths. ~99% accuracy.

**Shapely** — `MultiLineString.length` to sum a set of extracted line segments.

### Vision/AI

**Gemini Pro** — Foundation plan image → "Read the perimeter dimensions and total footing linear feet." ~75% accuracy. Suffers from scale errors.

**OpenCV + Hough lines** — Detect long continuous lines at consistent orientation (foundation walls). Sum pixel lengths → convert via scale. ~80% on clean drawings.

### Commercial

**PlanSwift** — Foundation takeoff with linear footing calculation. $1,749 one-time license. 2–3 minutes per plan. 35–40% faster than Bluebeam for takeoffs.

### Feasibility

| Approach | Accuracy | Effort | When to Use |
|---|---|---|---|
| PyMuPDF line extraction + geometry | ~90% | Medium | Vector CAD PDFs |
| ezdxf | ~99% | Low | DXF files available |
| Gemini Pro visual | ~75% | Low | Any PDF type |
| PlanSwift | ~99% | Low (manual) | High-volume, manual workflow |

**Recommended approach:** PyMuPDF line extraction for vector PDFs (already using PyMuPDF). This is the most direct path — we just need to add the geometric post-processing.

---

## 6. Labor Estimates

Requires: crew-hours per unit of work (per CY concrete, per LF framing, etc.).

### Industry Data Sources

**RSMeans Data Online** (Gordian) — The gold standard. 92,000+ unit cost line items with labor rates by trade and location. 970+ North American locations. Updated quarterly. No direct API — web-based subscription. Data structured by CSI MasterFormat division. Pricing: ~$500–2,000/yr depending on subscription tier.

**NAHB Fall 2025 Construction Labor Market Report** — Crew productivity data for residential construction. Publicly available PDF. Not an API but can be extracted and hardcoded as reference data.

**BLS API (Bureau of Labor Statistics)** — Wage and employment data for construction trades. Free API. Focus on pay rates, not productivity factors.

### Implementation Approach

Build a local labor factors table in PostgreSQL:
```
trade         | unit      | crew_hours_per_unit | source
--------------+-----------+---------------------+--------
Concrete pour | CY        | 1.2                 | RSMeans 2025
Form work     | SFCA      | 0.18                | RSMeans 2025
Wood framing  | LF wall   | 0.05                | RSMeans 2025
Sheathing     | SF        | 0.02                | RSMeans 2025
```

Apply burdened labor rate: base hourly rate × 1.25–1.45 (covers taxes, insurance, benefits).

### Feasibility

| Approach | Accuracy | Effort |
|---|---|---|
| RSMeans subscription + local table | 80–90% | Medium |
| NAHB data + manual coding | 75–85% | Low |
| GPT/Claude with labor factors prompt | 60–70% | Low |

**Recommended approach:** License RSMeans for the first year. Extract key residential trades (concrete, framing, sheathing, hardware install). Build local PostgreSQL table. Apply burdened rate multiplier. This is a one-time data entry task, not ongoing engineering.

---

## 7. Equipment Costs

Requires: crane, concrete pump, scaffolding estimates by project type.

### Industry Data Sources

**RSMeans Data Online** — Includes equipment rental rates and operator costs by region. Most reliable source for standardized equipment costs.

**Typical 2025 reference rates** (for internal table):
- Concrete pump: $100–300/hr + operator ($45–65/hr)
- Crawler crane (large): $2,000–5,000/day
- Scaffolding frame (20×50 ft, 4 weeks): $2,000–4,000 total
- Excavator operator: $38–55/hr
- Tower crane: $15,000–25,000/month

Note: Steel tariffs (Aug 2024) increased equipment costs ~25%. RSMeans 2025 data reflects this.

### Feasibility

No dedicated API for equipment costs. Best approach:
1. RSMeans subscription (covers equipment rental in cost data)
2. Internal reference table keyed by equipment type + project location
3. Quarterly refresh from RSMeans updates

**Accuracy:** 70–80% (regional variance is high; actual bids can differ 20–30% from reference rates).

---

## 8. Construction Schedule

Requires: phased timeline from structural scope of work.

### Libraries

**spaCy** (NLP) — Extract task names and durations from schedule documents or spec sections. Good for text-based schedule extraction.

**networkx** — Represent task dependencies as directed graph; calculate critical path automatically.

**IfcOpenShell** — Parse IFC (BIM) files for object-based schedule generation. Research-phase only — not production-ready for PDFs.

### Vision/AI

**Gemini Pro** — Read schedule table from PDF image. ~70% accuracy on typed schedules. Fails on handwritten or mixed formats. Use for extracting existing schedules from PDFs.

**GPT-4o / Claude** — Generate a phase sequence from extracted structural scope. No extraction needed — prompt: "Given these structural sheets and quantities, generate a typical construction phase schedule." Output is a reasonable starting point, not a verified schedule.

### Commercial

**Procore Project Planning** — Task scheduling integrated with estimating. No auto-import from PDFs; requires manual setup.

**Touchplan** — Visual scheduling tool. No PDF auto-import API.

### Feasibility

| Approach | Accuracy | Effort | Notes |
|---|---|---|---|
| Gemini Pro table reading | ~70% | Low | For existing schedule PDFs |
| GPT-4o phase generation | ~65% (coverage) | Low | Generated, not extracted; needs QA |
| spaCy NLP extraction | ~60–75% | Medium | Requires training vocabulary |
| BIM-based (IFC) | N/A | Very High | Not suitable for V1 |

**Recommended approach:** Use Claude/GPT-4o to generate a standard phase sequence from the extracted scope (what we already extract — sheet list, structural elements, special inspections). This is not extraction — it's inference. Flag it clearly as AI-generated and require Melvin's review before use.

---

## Key New Tool: PyMuPDF Vector Extraction

This is the biggest quick win we haven't used yet. We already have pypdfium2 for text extraction but PyMuPDF (`fitz`) can extract the vector graphics layer — the actual drawn lines. This opens up:

- Footing perimeter calculation (filter foundation plan lines, sum lengths)
- Sheathing area (reconstruct wall/floor polygons)
- Scale bar detection (auto-detect drawing scale from title block)

```bash
pip install pymupdf
```

```python
import fitz
doc = fitz.open("structural.pdf")
page = doc[page_num]

# Get all vector drawings
drawings = page.get_drawings()
# Each drawing: {"type": "l", "color": [0,0,0], "width": 0.5, "rect": ..., "items": [...]}

# Get text with position
blocks = page.get_text("dict")["blocks"]
# Returns text blocks with bbox coordinates — combine with drawings for dimension reading
```

This requires a moderate amount of custom geometry code but is the most direct path to extracting dimensions without paying for SaaS tools.

---

## Recommended V2 Roadmap

Based on this research, here's the suggested implementation priority:

### Quick wins (add to pipeline, 1–2 weeks each)
1. **PyMuPDF vector extraction** — Footing LF and sheathing area on CAD PDFs (~90% accuracy)
2. **PaddleOCR** — Better dimension text reading on plans (replaces pytesseract if needed)
3. **Gemini Pro** — Switch from GPT-4o for visual extraction on framing/foundation plans (~80% vs ~40%)

### Medium effort (2–4 weeks each)
4. **RSMeans labor/equipment table** — One-time data entry, enables labor + equipment cost estimates
5. **Shapely + OpenCV polygon area** — Sheathing sqft from floor plans
6. **Hybrid counting UI** — User selects region, Gemini counts members (~90% accuracy for lumber)

### High effort / V3 (4–8 weeks)
7. **Fine-tuned Florence-2** — Train on 100+ plan pages for specialized rebar/dimension extraction
8. **iBeam AI integration** — API integration for concrete/rebar (outsource to specialist)
9. **Schedule generation** — Claude generates phase sequence from extracted scope

---

## Sources

- PyMuPDF vector graphics extraction: https://artifex.com/blog/extracting-and-creating-vector-graphics-in-pdf-using-python-pymupdf
- PyMuPDF docs (drawings): https://pymupdf.readthedocs.io/en/latest/recipes-drawing-and-graphics.html
- PDFPlumber visual debugging: https://www.blog.brightcoding.dev/2025/09/29/pdfplumber-python-pdf-table-text-extraction
- AWS Textract vs Gemini on engineering drawings: https://www.businesswaretech.com/blog/benchmarking-ai-on-tables-and-engineering-drawings-results-findings
- Florence-2 fine-tuning for GD&T: https://arxiv.org/pdf/2411.03707
- PlanSwift vs Bluebeam 2026: https://constructionbids.ai/blog/planswift-vs-bluebeam-takeoff-software-comparison-2026
- RSMeans 2025 labor rates: https://www.rsmeans.com/2025-labor-rates-for-the-construction-industry-book
- iBeam AI concrete takeoff: https://www.ibeam.ai/subcontractors/concrete
- Procore Automated Area Takeoff (May 2025): https://www.procore.com/blog/simplifying-construction-estimating-with-automated-area-takeoff
- PaddleOCR vs Tesseract: https://ironsoftware.com/csharp/ocr/blog/compare-to-other-components/paddle-ocr-vs-tesseract/
- Floorplan-Dimractor: https://github.com/jasoncobra3/Floorplan-Dimractor
- NAHB Fall 2025 labor report: https://hbi.org/wp-content/uploads/2025/10/Fall-2025-Final-Construction-Labor-Market-Report-Update.pdf
- Equipment cost estimation 2025: https://constructionbids.ai/blog/equipment-costing-construction-bids
- OpenCV room dimension calculation: https://medium.com/@keerthivasanm20/room-dimension-and-area-calculation-using-python-opencv-e375474eaf2c
- ezdxf documentation: https://ezdxf.readthedocs.io/en/stable/tutorials/getting_data.html
