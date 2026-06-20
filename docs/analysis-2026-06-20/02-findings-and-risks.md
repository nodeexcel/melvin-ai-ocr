# 02 — Findings & Risks

**Session:** 2026-06-20 · Each finding states **evidence** and **impact**. "Verified" = checked directly against a file this session. "Likely-current" / "predates fix" indicates whether a JSON-artifact defect is probably still in current code.

Severity legend: 🔴 Critical · 🟠 High · 🟡 Medium · ⚪ Architectural/operational (quality, not user-facing yet).

---

## 🔴 Critical

### F-1 — Live public deployment with multiple security holes
**Evidence:** `melvin-testing-guide.md` documents a live app at **`http://116.202.210.102:20260`** with a registration page and shared invite code `melvin2026`. Code (verified prior session): `app/backend/app/main.py:22-23` → `allow_origins=['*']` **with** `allow_credentials=True` (invalid + dangerous combo); SSE auth accepts **JWT in `?token=` query string** (`deps.py`, `ProgressFeed.tsx`); JWT stored in `localStorage`; **no upload size limit** (`routers/projects.py`); **no rate limiting** anywhere; **plain HTTP** (no TLS in the documented URL).
**Impact:** Token theft via any XSS or any other origin; tokens leaked to logs/history; brute-forceable login; disk-exhaustion via large uploads (a 216 MB sample exists); credentials in plaintext on the wire. This is *active* exposure, not hypothetical.
**Note/correction:** secrets are **not** committed to git — `.gitignore` correctly excludes `.env`/`*.env` (verified). The real residual risk is that the OpenAI/Gemini keys were *sent over chat* (memory) and should be rotated.

### F-2 — Unverified/fabricated quantities returned unflagged (CLAUDE.md Rule 5 violation)
**Evidence (verified):** SVR JSON contains **0** occurrences of `"estimated"` yet emits joist/beam/hardware quantities. Woodlane JSON (per PDF review) emits **fabricated** wood hardware — "Hurricane ties HT-10 ×20", "Lag bolt LB-5 ×15", "MB-123 ×4", "A325 ×24" — none of which exist on the actual sheets (a steel-MF set), all unflagged, with round invented counts.
**Impact:** Directly violates the project's own non-negotiable Rule 5 ("never return unverified quantities… The client uses these numbers for real ordering"). Worse than missing data: it's *confidently wrong* data that could drive real orders. Note SVR predates the June estimated-flag work; Woodlane hallucination is a Vision behavior likely still present.

### F-3 — The OCR quantity path is broken in the environment that generated the artifacts
**Evidence (verified):** Paseo JSON (newest, 2026-06-18) contains **13** `ConvertPirAttribute2RuntimeAttribute` errors (PaddleOCR runtime failure) and **4** `parse_error`s; its `project` block is **fully empty** and concrete/nailing/lumber are all `0`. Memory documents the cause: PaddleOCR **crashes on Python 3.13** (the `app/backend/venv`) and only works on Python 3.11 / Docker.
**Impact:** The flagship capability for scanned PDFs (the whole reason OCR exists) produces nothing in the local/default environment. The "works in Docker" claim is real but **fragile and operator-hostile** — there is no guard that detects the broken runtime and warns; it silently degrades to empty. Anyone running outside the exact Docker image gets empty results that *look* like a clean run.

### F-4 — No reproducible extraction baseline; committed outputs are stale & inconsistent
**Evidence (verified):** the six `app/backend/scripts/output/*.json` are dated **2026-05-25 → 2026-06-18** and were produced by different code versions and environments. LHERT's committed output has `total_lf:0` though memory says "76.8 ft confirmed"; Paseo's has empty specs though the testing guide promises rich data. The "confirmed" successes exist only in **uncaptured** server/Docker runs.
**Impact:** You cannot trust the on-disk artifacts as a regression baseline, cannot prove current quality, and cannot tell whether a future change improves or regresses results. Every "done ✅" in `TODO.md` that rests on an uncaptured run is **unverifiable from the repo.** This undermines confidence in the entire status picture.

---

## 🟠 High

### F-5 — Production blocked by Gemini free tier (20 requests/day)
**Evidence:** `melvin-testing-guide.md` + `pipeline_state.md`: one LHERT run ≈ 11 Gemini calls; Woodlane committed run **lost 9 pages to 429** rate-limits. `GEMINI_CATEGORIES = {foundation, floor_framing, roof_framing}` route every plan page to Gemini.
**Impact:** Real usage is impossible on the free tier — ~1 PDF/day before quota exhaustion, with silent page-drops degrading results mid-run. Hard gate to any production use.

### F-6 — Project-info extraction errors (owner↔architect, empty on scanned)
**Evidence (verified):** SVR `architect: "RODNEY MESRIANI"` (he is the **owner**); SVR `total_sqft: 33030` (a zoning-allowable figure, not building area). Paseo `project` block fully empty despite legible cover.
**Impact:** Wrong/blank metadata on client-facing reports; `total_sqft` errors propagate into the quantity estimates that depend on floor area.

### F-7 — Real structural data missed on complete sets
**Evidence:** SVR — populated **S1.3 Roof Framing** (J-1…J-7 schedule, glulams) yields empty `roof_framing`. Whaleon — **Basement Wall Schedule** and **Shear Wall Schedule** absent from output; complete set still falls back to **2000 sqft default**. LHERT — concrete spec & 5/8" anchor bolts missed.
**Impact:** Even within the achievable (spec/schedule) envelope, extraction is incomplete and inconsistent. The product underdelivers on data it *could* reliably get.

### F-8 — Output noise: cross-discipline & placeholder pollution persists in stored data
**Evidence (verified):** Paseo JSON still contains noise codes **AB123 ×7, LS456 ×4, PSS1 ×6** (memory claims these were "filtered"). LHERT `roof_framing.hardware` carries LUTRON/LEVITON (electrical). Woodlane carries steel weld codes.
**Impact:** The noise *filter lives in `generator.py` (render time)*, so the **stored `raw_json` remains polluted** — any consumer reading `raw_json` (the `/cost-estimate` endpoint, the results page, future integrations) sees the noise. This is an architecture smell: filtering at the presentation layer, not the data layer. It's also an ever-growing **denylist** (dozens of hardcoded brand/code strings) — the opposite of the "real solution, not patches" principle in `feedback_no_patches.md`. An **allowlist of valid Simpson model patterns** would be the root-cause fix.

### F-9 — The core requirement (quantity takeoff) has a hard physical ceiling
**Evidence:** §3 of `01`; confirmed on the gold-standard LHERT SONG — hardware quantities and member counts exist only as distributed graphical callouts, not text/schedules.
**Impact:** Requirements 1, 6 (quantities), 7, 9 cannot be met by the current text/OCR approach regardless of effort. Closing it needs **DXF/CAD layer files**, **vector-geometry counting**, or a **specialist service** (iBeam AI) — each with real cost/accuracy trade-offs (see `research-extraction-approaches.md`). This must be a *scope decision*, not a backlog item.

### F-10 — No project-type / scope detection (wood vs steel; CD vs DD)
**Evidence:** Woodlane (steel-MF) produced fabricated wood hardware; BARAGHOUSH (DD) produced a silent empty result.
**Impact:** The system neither declines out-of-scope inputs nor explains in-scope-but-empty ones. Both erode trust on a user's first upload — the exact moment that matters with an already-skeptical client.

---

## 🟡 Medium

### F-11 — Specification has drifted from reality, undocumented
**Evidence:** Design spec (`2026-05-20`) names **Claude Sonnet 4.5** vision, **pdf2image + poppler**, **python-jose**, "5–10 min" processing. Reality: **GPT-4o + Gemini 2.5-flash**, **pypdfium2 + PaddleOCR**, **PyJWT + pwdlib**, "20–45 min" (`melvin-testing-guide.md`). The `raw_json` schema in the spec (flat `floor_framing.lumber[]`, etc.) also differs from what aggregate.py now produces (phase dicts, nested schedules).
**Impact:** The design spec is no longer a usable source of truth; onboarding/handover off it would be actively misleading. Per CLAUDE.md Rule 7, docs are supposed to be the source of truth.

### F-12 — Processing time & UX for long/large jobs
**Evidence:** 20–45 min/PDF; 216 MB file; SSE progress is the only feedback.
**Impact:** Long waits with a single failure mode (lose Gemini quota mid-run → partial result). No resumability; a 429 at page 50 wastes the whole run's spend.

### F-13 — Schedule-table-OCR plan rests on an unproven premise
**Evidence:** `docs/PLAN.md` Priority 1 assumes schedule tables yield exact hardware quantities (cites Paseo grade-beam schedule). Ground-truth: the **gold-standard LHERT set has no quantity column in any schedule** (verified by PDF review). The Paseo grade-beam quantity claim is unverified (and Paseo's OCR is broken anyway).
**Impact:** A planned, "high-value, achievable-now" workstream may deliver far less than expected. Worth validating the premise per-firm before investing.

### F-14 — DD/empty-result UX (no explanation)
**Evidence:** BARAGHOUSH returns ~empty in ~2 s; document has "NOT FOR CONSTRUCTION" on every page and no S-sheets.
**Impact:** Indistinguishable from failure to the user. Low-effort, high-trust fix available (detect & explain).

---

## ⚪ Architectural / operational (carried from prior code review, re-confirmed relevant)

- **A-1 Silent error swallowing** — `runner.py` catches extraction exceptions into `{"error": str(e)}` and continues; no structured logging in the pipeline. Failures look like successes (root cause behind F-3/F-7 going unnoticed).
- **A-2 No schema validation** — extraction returns untyped dicts threaded through aggregate → quantities → cost; malformed LLM output propagates silently. A Pydantic boundary would catch it.
- **A-3 Filtering at the presentation layer** (F-8) — data-quality logic belongs in aggregate.py, not generator.py.
- **A-4 In-place mutation** — `aggregate.inject_lf_data` mutates the result dict with no copy; implicit side effects.
- **A-5 Magic numbers scattered** — DPI 250, TEXT_HEAVY_MIN_CHARS 2000, TILE_SIZE 2000, waste %s, 2000-sqft default, dedup distances — spread across 8 files, no constants module.
- **A-6 PDF rendered twice** — thumbnails (classify) + full-res (extract); cacheable.
- **A-7 Fragile environment split** — `venv/melvin311` (Py 3.11, PaddleOCR ✅) vs `app/backend/venv` (Py 3.13, PaddleOCR ✗) vs Docker (Py 3.11 ✅, via libgomp1/libgl1). Easy to run in the wrong one and silently lose OCR (F-3). Two committed venvs also bloat the working tree.
- **A-8 Single-user scale assumptions** — `ProcessPoolExecutor(max_workers=2)`, `shutdown(wait=False)` (jobs lost on restart), DB-polling SSE every 500ms. Fine for one user; not for concurrency.
- **A-9 No observability** — no request logging, correlation IDs, or run manifests; combined with F-4 there's no way to audit what produced a given result.

---

## Risk register (consolidated)

| ID | Risk | Likelihood | Impact | Priority |
|---|---|---|---|---|
| F-1 | Live app exploited / keys abused | Med | High | **Now** |
| F-2 | Wrong quantities drive a real order | Med | High | **Now** |
| F-3 | Scanned PDFs silently extract nothing | High | High | **Now** |
| F-4 | Can't prove/repro quality; regressions invisible | High | High | **Now** |
| F-5 | Quota exhaustion blocks real use | High | High | Near |
| F-9 | Core takeoff requirement unmeetable as-built | Certain | High | Decision |
| F-6/7/8 | Incomplete/incorrect/noisy in-scope output | High | Med | Near |
| F-10 | Trust loss on first upload (wrong/empty) | Med | Med | Near |
| F-11 | Spec misleads handover | Certain | Med | Cheap fix |
| F-12 | Long-run failure wastes spend | Med | Med | Later |
