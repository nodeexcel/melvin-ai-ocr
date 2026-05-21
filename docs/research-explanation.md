# What the Research Means — Plain English Explanation

**Date:** 2026-05-21  
**Purpose:** Explain what `research-extraction-approaches.md` says in simple terms — what the gaps are, what tools exist to fix them, and what we should actually do.

---

## The Core Problem

Our pipeline is great at reading **text** in PDFs — material specs, hardware model numbers, nailing schedules. But a lot of the information Melvin needs comes from **drawings** — the actual lines, dimensions, and layouts on the plans. You can't read a drawing the way you read a sentence.

Here's the breakdown: **8 things the client wants that we currently can't reliably deliver.**

---

## 1. Concrete Cubic Yards (CY)

**Why we can't do it now:** To calculate concrete volume, you need: footing width × footing depth × total linear feet of footings. We already extract the width and depth from spec text. The missing piece is linear feet — that's drawn on the foundation plan as lines and dimension callouts, not written as a number anywhere.

**How to fix it:**

| Option | What it does | Accuracy | Cost |
|---|---|---|---|
| PyMuPDF line extraction | Read the actual drawn lines from the PDF and measure them mathematically | ~90% | Free (code to write) |
| Gemini Pro (AI vision) | AI looks at the drawing image and estimates dimensions | ~80% | ~$0.01–0.05/page |
| iBeam AI (specialist service) | Upload PDF, they calculate CY for you | 90–98% | $150–500 per estimate |
| DXF file (AutoCAD export) | If the engineer gives us the CAD file, near-perfect calculation | ~99% | Free |

**Our recommendation:** Use PyMuPDF to extract the drawn lines and do the math ourselves. This is the biggest quick win we haven't tried yet. It's 2 weeks of engineering work and then it's free forever.

---

## 2. Rebar Linear Feet + Count

**Why we can't do it now:** Rebar is shown on drawings as bar callouts (#4 @ 12" OC), schedules (tables of bar marks), and layout lines. We currently read the spec (grade, spacing) but not the total quantity.

**How to fix it:**

| Option | What it does | Accuracy | Cost |
|---|---|---|---|
| Gemini Pro on rebar schedule | AI reads the rebar schedule table and calculates totals | ~75–80% | API cost |
| PaddleOCR | Better OCR tool for reading dimension text in rotated callouts | ~70% | Free |
| Fine-tuned Florence-2 | Train a specialized AI on 100+ rebar plan pages | ~85–90% | Free (but 4–6 weeks training work) |
| iBeam AI rebar tool | Specialist service — reads callouts, adds lap splices per ACI code | 90–98% | $200–400/job |

**Our recommendation:** Use Gemini Pro on rebar schedule pages first (easy, low cost). For production accuracy, consider iBeam AI.

---

## 3. Lumber Piece Counts

**Why we can't do it now:** Lumber counts (how many 2x10 joists, how many beams) require counting individual members on framing plan drawings. These are complex, dense drawings with lots of overlapping elements.

**How to fix it:**

| Option | What it does | Accuracy | Cost |
|---|---|---|---|
| Gemini Pro + guided counting | AI counts members in a specific drawing region | ~70–75% | API cost |
| Train a custom AI model (YOLO) | Computer vision model trained to detect framing symbols | ~80–85% | Free but 4–6 weeks to train |
| Hybrid UI (user points, AI counts) | Melvin clicks on a region of the plan, AI counts within it | ~90% | API cost |

**Our recommendation:** Build a hybrid UI where Melvin selects the area of the plan and types a hint ("count 2x10 joists at 16\" OC"). The AI counts within that region. This gives the best accuracy with the least engineering, and keeps Melvin in control.

---

## 4. Sheathing Square Footage

**Why we can't do it now:** Sheathing area = total wall area + roof area. These are never written as numbers in structural PDFs. You'd have to measure the floor plan and roof plan drawings.

**How to fix it:**

| Option | What it does | Accuracy | Cost |
|---|---|---|---|
| OpenCV + Shapely (code) | Extract wall outlines from the drawing, calculate polygon area | ~90% | Free |
| Gemini Pro visual | AI looks at floor plan and estimates total area | ~75–80% | API cost |
| Procore Takeoff API | Procore's auto-measure feature does it with a button click | ~95% | Procore subscription |

**Our recommendation:** OpenCV + Shapely for vector PDFs (CAD-generated). Gemini Pro fallback for scanned plans. This is 2–3 weeks of work.

---

## 5. Footing Linear Feet

**Why we can't do it now:** The total length of footings is shown as a layout drawing — you'd have to trace the foundation plan and add up all the footing lines.

**How to fix it:** This is actually the easiest of the quantity problems. PyMuPDF can read the drawn lines directly from CAD-generated PDFs. We filter for footing lines → measure their lengths → add them up. ~90% accuracy. We already use PyMuPDF for other things — this is just adding a new step.

**Our recommendation:** Add PyMuPDF line extraction on foundation pages. This is the highest-value, lowest-risk improvement we can make.

---

## 6. Labor Estimates

**Why we can't do it now:** Labor estimates aren't in PDFs. They come from industry data — how many crew-hours does it take to pour 1 cubic yard of concrete? That data has to come from somewhere.

**The industry source everyone uses:** **RSMeans** — a database of 92,000+ construction costs, updated quarterly. It's the standard reference in the industry. The catch: there's no free API. It's a subscription ($500–2,000/year).

**What we'd build:** A table in our database with values like:
- Pour concrete: 1.2 hours per CY
- Wood framing: 0.05 hours per LF of wall
- Sheathing: 0.02 hours per SF

Then multiply extracted quantities by those factors. Apply a multiplier for taxes and insurance (×1.25–1.45 of base rate).

**Our recommendation:** License RSMeans, extract the key residential construction trade rates, build a local table. One-time setup, then it works automatically.

---

## 7. Equipment Costs

**Why we can't do it now:** Same reason as labor — it's not in the PDFs. Equipment costs (concrete pump, crane, scaffolding) depend on project type, location, and duration.

**Rough reference rates (2025):**
- Concrete pump: $100–300/hr
- Crawler crane: $2,000–5,000/day
- Scaffolding (4 weeks): $2,000–4,000
- Excavator operator: $38–55/hr

Note: Steel tariffs (mid-2024) increased equipment costs by ~25%, so older data is stale.

**Our recommendation:** RSMeans covers equipment costs too, so same plan as labor — one subscription handles both. We'd build a lookup table keyed by equipment type + project region. Accuracy is ~70–80% (equipment costs vary a lot by location).

---

## 8. Construction Schedule

**Why we can't do it now:** A construction schedule (which work happens in what order, how long each phase takes) can't be read from structural PDFs. It has to be built from the scope.

**What we can do:** We already extract the sheet list, structural element types, and special inspections. We can use Claude/GPT-4o to generate a standard phase sequence from that information. It won't be a project-specific schedule — it will be a typical sequence for this type of work. 

Example output: "Phase 1: Site prep + excavation (2 weeks). Phase 2: Foundation + footings (3 weeks). Phase 3: Framing (4 weeks)..."

**Accuracy:** ~65–70% — it will be reasonable but Melvin must review and adjust it. It's a starting point, not a finished schedule.

**Our recommendation:** Use Claude to generate a phase sequence from the extracted scope. Flag it clearly as AI-generated. Require Melvin's review before use. Low effort, useful as a starting point.

---

## What This Means for the Build Plan

### Things we can add quickly (1–2 weeks each, high value):

1. **PyMuPDF vector line extraction** — Gets us footing LF and enables CY calculation. Biggest quick win. We already use PyMuPDF, just need to add geometry math.

2. **Switch to Gemini Pro for vision pages** — Accuracy jumps from ~40% (GPT-4o) to ~80% (Gemini) on technical drawings. Cost is similar.

3. **PaddleOCR** — Better at reading rotated dimension text and callouts than what we use now.

### Things that take more work (2–4 weeks each):

4. **RSMeans labor + equipment table** — One-time data entry. Enables cost estimation.
5. **OpenCV + Shapely for areas** — Sheathing sqft from floor plan outlines.
6. **Hybrid counting UI** — User selects region, Gemini counts. Best accuracy for lumber.

### Things that are a bigger project (4–8+ weeks):

7. **Fine-tuned Florence-2** — Train a specialist AI on construction plans. Best long-term accuracy but requires 100+ annotated plan pages as training data.
8. **iBeam AI integration** — Pay a specialist service to handle concrete/rebar takeoff. High accuracy, low engineering, but ongoing cost per job.
9. **Full schedule generation** — Build proper phase sequencing with durations.

---

## Bottom Line

| What Melvin Wants | Can We Do It Now? | Best Path to Get There |
|---|---|---|
| Material specs (concrete PSI, lumber grade) | ✅ Yes, works today | — |
| Simpson hardware model numbers | ✅ Yes, works today | — |
| Framing connection details | ✅ Yes, works today | — |
| Nailing schedules | ✅ Yes, works today | — |
| Footing linear feet | ⚠️ Not yet | Add PyMuPDF geometry (2 weeks) |
| Concrete cubic yards | ⚠️ Not yet | PyMuPDF LF + spec math (2–3 weeks) |
| Rebar linear feet | ⚠️ Not yet | Gemini Pro on schedules (1–2 weeks) |
| Lumber piece counts | ⚠️ Not yet | Hybrid UI with Gemini (2–3 weeks) |
| Sheathing square footage | ⚠️ Not yet | OpenCV + Shapely (2–3 weeks) |
| Labor estimates | ⚠️ Not yet | RSMeans table (2 weeks + subscription) |
| Equipment costs | ⚠️ Not yet | RSMeans table (same subscription) |
| Construction schedule | ⚠️ Partial | AI-generated starting point (1 week) |

The first 4 items are solid today and ready to ship. The rest can be added incrementally — none of them are impossible, they just need engineering time and in some cases a data subscription (RSMeans).
