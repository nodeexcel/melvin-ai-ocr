# 07 — Client Feedback: Melvin Meeting 2026-06-23

**Source:** screen-share walkthrough, transcribed (Whisper) from `~/Downloads/2026-06-23 13-02-03.mp4`. First substantive client feedback in the project. Overall sentiment **positive**: *"so far it's looking good, I like what I see, it just needs a little more detail to polish."*

> This meeting **resolves the scope fork** (`04-open-questions` Q-1) and **confirms** findings F-2 (hallucination) and F-9 (quantities = the product). It supersedes the "client unresponsive" framing in earlier docs.

---

## 1. Decisive scope pivot — TAKEOFF ONLY

Melvin's clearest direction: **this app should produce a material takeoff and nothing else.**

- *"On this app, what I want is only the list for material. Just takeoff for concrete, rivers [rebar], all the hardware, steel, and lumber. That's it."*
- *"If you can focus only on takeoff, I don't need the price… the labor I can figure out later, we can do another app just for that."*
- *"I don't want a heavy app. I want apps for every trade."* → pricing, labor, schedule = **separate future apps**, one per function/trade.

**Consequence for the codebase:** the Phase-3 features (rate sheet, `cost_estimate.py`, labor estimate, equipment costs, the cost section in the PDF + results page) are **out of scope for this app.** Not deleted — relocated to a future "pricing" app. The current report should **stop showing cost/labor**.

This answers the long-open Path-A/B/C question (`02`/`04`): the client wants **full takeoff *with quantities*, no pricing**.

---

## 2. Confirmed working ✅ (do not regress)

- **Wall stud estimates** — ext 2x6 base 385 +10% = 423; int 2x4 578 +10% — *"sounds right."*
- **Wall sheathing** 53 sheets — correct. **Roof sheathing** — fine.
- **Table format** (hardware = model + qty; plywood with length) — *"super easy for me, my sales guy, my supplier."* Keep it.
- The pipeline **correctly identifies** the right hardware models, connections, and which detail/phase they belong to.

---

## 3. Defects & gaps (client's own words)

| # | Issue | Detail |
|---|---|---|
| M-1 | **Hallucinated hardware variants** (= our F-2, client-confirmed) | Report invented hold-down/rod sizes 15/18/21/24 ("HFX"); *"we don't have those, it's only one dimension."* He hand-counted **14** of the one real size. Confidently-wrong data is his top complaint. |
| M-2 | **No quantities** (the recurring theme) | *"It's reading everything, but I need the quantity."* Needed for every hardware item (ECCQ, A35, lag screws, EPC/ECCQ caps, HUCQ hangers, hold-downs), beams, rebar, concrete. |
| M-3 | **Beams/headers entirely missing** | Needs all framing-schedule beams/headers/posts with **size + length**: header3=4x10, CV6=4x8, CV2/CV3/CV7/CV8, header4/5, etc. The report had **no beams**. |
| M-4 | **Rebar quantity missing** | Foundation shows #4 top/bottom reinforcement but no quantity. |
| M-5 | **Total concrete CY missing** | Showed only 3.4 CY; needs the **whole-project total** (all footings + slab). |
| M-6 | **Wrong plywood type** | Listed T&G 3/4" plywood that isn't on the plan. |
| M-7 | **Formatting** | Put **size+length in FRONT** (`2x6x10`, `2x6x12`); hardware dims as width×height, height/length up front; trim empty columns/space. So a supplier reads it directly. |

---

## 4. The core feature request — detail-callout extraction

The heart of what he's paying for. Melvin demonstrated his manual estimator workflow (Bluebeam-style tool; details turn **red** once accounted for):

1. Plans are covered in **detail callout markers** — e.g. *"detail 8 → sheet S4.1"*, *"detail 7 → S0.40"*.
2. He clicks a callout → jumps to that **detail**, which specifies the hardware: post base (BC/CBSQ), straps (833/835/ST), ECCQ, EPC/ECCQ caps, HUCQ hangers, A35, **lag bolts "per shear-wall schedule"**, hold-downs, hip/joist hangers.
3. He **counts how many times each callout appears** on the plan → that count = the **quantity** of that connection's hardware.
4. He follows **secondary references** too (a detail that says "lag screw per shear-wall schedule" → he reads the shear-wall schedule for spacing/size).

**His ask:** the app should detect **every** detail callout, resolve each to its detail sheet, extract that detail's hardware, follow secondary references, and **total the quantities** — i.e. automate steps 1–4.

**Why this is the key insight (engineering note):** our analysis (`02` F-9, `05` R1) framed the quantity problem as *"count 410 unlabeled LUS210 joist hangers"* — which frontier vision models fail at (AECV-Bench 0.40–0.55). Melvin reframes it as *"count discrete, **labeled** callout markers + read each referenced detail."* Detecting/OCR-ing labeled bubble markers and resolving cross-sheet references is a **structured, tractable** problem — not blind symbol counting. **This is a viable path to the quantities, and it mirrors how estimators actually work.** It should be the centerpiece of the takeoff engine.

---

## 5. Wanted at upload (input metadata)

- **Square footage**; **new construction vs remodel vs addition** (the test plan was an *addition*, "4380U", to an existing house).
- Read **elevations** to recover correct **stud lengths** (e.g. a 2x12 wall region → right lengths for the 2x4/2x6).
- **Steel** is in scope when present ("steel, if we have steel").

---

## 6. Target output format (explicit)

A clean per-line **`Qty | Size | Length | Description`** list, like a lumberyard quote (he showed a supplier's quote he likes). Examples he praised: `HDU14 — qty`; plywood `4x8x12` with description. No extra columns or whitespace. Organized for a supplier to read and order directly. (Consistent with the Ganahl EST618017 gold standard in `06`/`procurement_format`.)

---

## 7. Logistics / action items

- **Melvin will:** enable **billing on his Gemini key** + add **credit to his OpenAI key** (unblocks quota finding F-5; dev had been self-funding), and send **more sample PDFs**.
- **Dev will:** re-scope the app to takeoff-only, fix hallucination, add beams/rebar/concrete quantities, build detail-callout extraction.

---

## 8. Re-prioritized roadmap (from his feedback)

1. **Strip pricing/labor**; output the clean Qty|Size|Length|Description material list. *(low effort, high signal)*
2. **Kill hallucinations** — only emit hardware/sizes actually present; flag estimates (F-2 / Rule-5). *(trust gate)*
3. **Extract beam/header schedule** (size + length) — M-3.
4. **Detail-callout extraction engine** — detect → resolve → extract → count → quantities. *(the product; §4)*
5. **Foundation quantities** — total concrete CY + rebar qty — M-4/M-5.
6. **Upload metadata** — sqft, project type, elevation-based stud lengths — §5.
7. Onboard his keys + new sample PDFs.

Items 1–3 make the next demo land; item 4 is the core engineering effort and now has a tractable approach.

---

## Appendix — Whisper transcription glossary
The auto-transcript garbled construction terms; decoded for future reference:
- **"rivers" → rebar** ("rebars", Spanish-accented)
- **"cheating" → sheathing** ("while cheating"→ wall sheathing; "roof cheating"→ roof sheathing)
- **"heap" → hip / hanger callout** (roof hip or a tagged connection)
- **"HFX" → a hold-down/rod hardware tag** (transcription approximate; the holdown/rod he counted 14 of)
- **"833 / 835 / A35" → Simpson clips/straps**; **"ECCQ / EPC / HUCQ"** → Simpson caps/hangers (real models)
- **"4380U" → the project/plan number** (an addition project)
