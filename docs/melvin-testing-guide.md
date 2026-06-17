# Mel's Builders Pro Systems — Testing Guide

**App URL:** http://116.202.210.102:20260

---

## Step 1 — Create Your Account

1. Go to **http://116.202.210.102:20260/register**
2. Enter a username — e.g. `melvin`
3. Enter a password of your choice
4. Invite code: **`melvin2026`**
5. Click **Create Account**

You'll land on the dashboard automatically.

---

## Step 2 — Set Your Labor & Equipment Rates

1. Click **Rate Sheet** in the top-right corner of the dashboard
2. Fill in your actual costs per unit

### Labor Rates

| Field | What It Means | Sample Rate |
|-------|--------------|-------------|
| Wall Studs | Labor to frame one stud | $13 / piece |
| Subfloor Plywood | Install one 4×8 sheet | $35 / sheet |
| Wall Sheathing | Install one 4×8 sheet | $28 / sheet |
| TJI / I-Joists | Install one engineered floor joist | $22 / piece |
| Concrete (pour + finish) | Total labor per cubic yard | $475 / CY |
| Excavation | Per linear foot of footing trench | $9 / LF |
| Hardware Install | Per Simpson connector installed | $5 / piece |

### Equipment Rates

| Field | What It Means | Sample Rate |
|-------|--------------|-------------|
| Concrete Pump | Pump rental cost per CY poured | $35 / CY |
| Crane / Lift | Equipment cost per sqft of floor area | $0.85 / sqft |
| Scaffolding | Per sqft of exterior wall area | $1.20 / sqft |

3. Click **Save Rates**
4. You'll see a green confirmation message

> **Note:** Replace the sample rates above with your actual numbers. These are stored to your account and automatically applied to every report you download.

---

## Step 3 — Upload a PDF and Run the Pipeline

1. Click **+ New Estimate** on the dashboard
2. Enter a project name (e.g. `Whaleon Residence`)
3. Drag and drop or browse to select a structural plan PDF
4. Click **Upload**
5. You'll be taken to a live progress screen — wait for it to reach 100%
6. Processing time: **5–45 minutes** depending on PDF size
7. Once complete, click **View Results**

---

## Step 4 — What to Expect From Each PDF

### ✅ Whaleon Residence CD Set
> **Start here. Fastest run (~25 min). Cleanest results.**

- Hardware split by phase: HDU hold-downs in Foundation, LUS joist hangers in Floor, MST/CMST straps in Wall, H1/H2.5A hurricane ties in Roof
- Foundation: footing types, rebar specs, estimated linear feet and CY
- Preliminary quantities: studs, plywood (all 3 types), cost breakdown
- 50+ framing connection details

---

### ✅ 571 Paseo Miramar RTI Stamped Plans
> **Scanned plans. Good hardware and foundation data. ~20 min.**

- Hardware: 40+ items across all phases
- Foundation: 128.6 ft footing LF, 10.7 CY concrete, 8 footing types with full rebar specs
- Cost estimate: all line items showing
- ⚠️ **Known limitation on scanned plans:** Architect and Structural Engineer names may be blank. Concrete PSI values may be missing. This is because scanned PDFs don't have a readable text layer — we are working on a fix.

---

### ✅ LHERT SONG CD Bid Set
> **Most detailed structural data. ~30 min.**

- Hardware: wall straps (CMST12, CMST14), hold-downs (HDU2–HDU14), TJI floor joists
- PSL engineered beams with span lengths
- Connections: 100+ framing details
- ⚠️ **Google API limit:** The free Google key allows 20 requests per day. Running LHERT SONG uses about 11 of those. If a run fails partway through, wait until the next day or upgrade the Google API key to a paid plan at [aistudio.google.com](https://aistudio.google.com).

---

### ✅ SVR 80% CD Set (167 pages)
> **Largest PDF. ~45 min. Good stress test for a big job.**

- Dense nailing schedule, many framing connections, large hardware list
- ⚠️ Takes longest — start it and come back

---

### ✅ BARAGHOUSH DD Progress
> **Architectural only. Should return zero structural data.**

- This is a design-development set with no structural engineer drawings
- Expected result: 0 hardware, 0 connections
- This is correct — confirms the app doesn't make up data that isn't there
- Good sanity check to run

---

## What the Report Contains

Once processing is complete, click **Download PDF Report**. You'll get a 3–6 page report with:

| Section | What it Shows |
|---------|--------------|
| **Hardware Schedule by Phase** | Foundation / Floor / Wall / Roof hardware with quantities |
| **Preliminary Quantities** | Estimated studs, plywood sheets based on floor area |
| **Preliminary Labor Estimate** | Your rates × extracted quantities = cost per line item |
| **Foundation** | Footing types, width/depth, rebar specs, total LF and CY |
| **Floor Framing** | Joist sizes, beam sizes with spans |
| **Nailing Schedule** | Nail sizes and patterns from the plans |
| **Framing Connection Details** | 50–160 connections with hardware and lumber sizes |

The cost estimate also appears **directly on the results page** — no need to download the PDF just to see the numbers.

---

## What We Are Still Working On

These are known issues. They won't stop the app from running — you'll just see less data in those specific fields:

| Issue | Which PDFs | Notes |
|-------|-----------|-------|
| Architect / SE name blank | Scanned PDFs (Paseo Miramar) | Fix in progress |
| Concrete PSI values missing | Scanned PDFs | Fix in progress |
| Footing LF numbers being corrected | All PDFs | Bug found — numbers may be slightly off in current runs, fix ready to deploy |
| Unknown hardware codes | All PDFs | See below |

---

## One Thing We Need Your Help With

In the **General / Connections Hardware** section of the report, you may see codes like:

- **AB123** — is this a real Simpson model or a drawing label?
- **LS456** — same question
- **AB6**, **JH456**, **SP789**, **BP3** — real models or placeholders?

If any of these are real Simpson models you use, let us know and we'll make sure they show up correctly. If they're not real, we'll add them to the filter.

---

## Quick Reference

| | |
|--|--|
| **App URL** | http://116.202.210.102:20260 |
| **Register URL** | http://116.202.210.102:20260/register |
| **Invite Code** | `melvin2026` |
| **Rate Sheet** | Top-right corner after login |
| **Expected run time** | 20–45 min per PDF |
| **Cost per run (API)** | ~$0.05–0.30 depending on PDF size |
