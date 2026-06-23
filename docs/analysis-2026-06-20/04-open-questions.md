# 04 — Open Questions / External Inputs Needed

**Session:** 2026-06-20. What blocks *confidence* in a future implementation.

> **⚡ UPDATE 2026-06-23 — many of these are now ANSWERED by the client (see `07-melvin-meeting-2026-06-23.md`):**
> - **Q-1 (quantity-takeoff scope) — RESOLVED:** full takeoff *with quantities*, **no pricing/labor** in this app. Quantities are the whole point.
> - **Q-3 (hardware: models vs counts) — RESOLVED:** exact **counts required** (he hand-counts today); approach = detail-callout detection + counting.
> - **Q-4 (report format) — RESOLVED:** clean `Qty | Size | Length | Description`, size+length in front, no pricing columns.
> - **Q-7 (steel scope) — RESOLVED:** steel **is** in scope when present.
> - **Labor/equipment/schedule — DE-SCOPED** from this app → separate future per-trade apps.
> - **API keys (F-5) — being unblocked:** Melvin enabling Gemini billing + OpenAI credit.
> - Still open: exact detail-callout marker formats across firms; per-project metadata capture (sqft, new/remodel/addition); his rate sheet (now only relevant to the future pricing app).
>
> The original framing below (client unresponsive, proceed on defaults) applied up to 2026-06-20 and is retained for history.

---

## A. Clarifications needed from Melvin (with default if no answer)

The six questions in `docs/findings-and-feasibility.md §8` were never answered. They remain the real requirement gaps.

| # | Question | Why it matters | Recommended default (if silence) |
|---|---|---|---|
| Q-1 | **Quantity-takeoff scope** — does he need AI-generated quantities, or will he enter them himself? | Defines the whole product (Path A/B/C, F-9) | **Path C**: estimate + clearly flag; he adjusts from experience. Document it. |
| Q-2 | **Accuracy threshold & review workflow** — what's the consequence of an extraction error; will he always review? | Governs how aggressively to estimate vs withhold | Assume **always-review**; never present a number as order-ready; show provenance. |
| Q-3 | **Hardware quantities** — are model lists enough, or are exact counts required for ordering? | Determines if F-9 is a dealbreaker | Assume **counts desired but not blocking**; ship models + flagged estimates. |
| Q-4 | **Report format** — does he want the Ganahl phase-organized format with prices? | Output shape (currently type-organized, not floor-organized) | Move toward **phase/floor organization**; omit prices (no price source). |
| Q-5 | **PDF mix** — mostly digital or also scanned/stamped? | Prioritizes OCR robustness (F-3) | Assume **both**; treat scanned reliability as required, not optional. |
| Q-6 | **Unknown codes** — already partly answered (AB123/LS456/etc. confirmed *not* real, per memory). | Noise filtering | Treat as resolved; move to allowlist approach (C-R5). |

**New questions surfaced by this analysis:**
- Q-7 — **Steel-moment-frame projects (e.g. Woodlane): in scope or not?** His stated scope is wood foundation/framing. *Default:* out of scope → detect and decline rather than fabricate (F-2/F-10).
- Q-8 — **Does he ever receive DXF/CAD files** from his engineers? This is the only near-perfect path to real quantities (C-R10). *Default:* assume no; don't build for it until confirmed.

---

## B. Missing files / assets

- **B-1 — Source PDFs are not in the repo.** They live in `~/Downloads/` on the dev machine (now identified). They are gitignored-by-absence; any clean checkout cannot reproduce results. *Impact:* contributes to F-4. *Need:* a stable, version-controlled (or documented external) fixture location.
- **B-2 — The real Ganahl order PDF (#618017) is not in the repo** — only transcribed into `memory/procurement_format.md`. *Impact:* the gold-standard target can't be diffed against output programmatically. *Need:* the PDF (or a structured transcription) checked into a fixtures area for scoring.
- **B-3 — No captured, environment-tagged run outputs** (F-4). *Need:* see C-R1.
- **B-4 — No DXF/CAD files** for any sample project. *Need (optional, Path B only):* at least one DXF to evaluate the only high-accuracy quantity route.

## C. Missing specifications

- **C-1 — Target report layout** is not specified beyond "match Ganahl" (Q-4). Need a concrete template (sections, columns, what's omitted).
- **C-2 — Accuracy/QA acceptance criteria** are undefined (Q-2). Without a target ("X% of lines within Y% of final order"), "done" is unfalsifiable. `PLAN.md` proposes 70–80% line match — needs client confirmation or adoption as the internal bar.
- **C-3 — Provenance/flagging contract** for estimated vs read values is implied by Rule 5 but not specified as an output schema field (C-R3).

## D. Access / credentials

- **D-1 — Production server** `116.202.210.102:20260` — deployment access, TLS setup, and who operates it are not documented in-repo. *Need:* clarify ownership and access for the security hardening in C-R4.
- **D-2 — Gemini paid-tier billing** (F-5) — a paid key requires a billing-owner decision (Melvin's account vs developer's). Currently the developer self-funds (`client_responsiveness`). *Blocker for production.*
- **D-3 — API key rotation** — OpenAI + Gemini keys were sent over chat (memory) and should be rotated; the current `.env` holders need to coordinate.

## E. External dependencies

- **E-1 — RSMeans** (or NAHB data) for credible labor/equipment factors. The cost engine currently uses Melvin's manual rate sheet only; the spec's "labor estimate" ideally wants productivity factors (`research-extraction-approaches.md §6–7`). Subscription/cost decision.
- **E-2 — iBeam AI / Rebar.Shop** — only realistic path to production-grade concrete/rebar quantities ($150–500/job). Procurement decision, Path B only.
- **E-3 — Gemini paid tier** (= D-2).
- **E-4 — Poppler / PaddleOCR system libraries** — see environment section below.

---

## F. Environment & tooling — gaps and required OS-level dependencies

Per the session's environment protocol: I did **not** install anything, did **not** use `sudo`, and treated the host as read-only. The following are **documented, not actioned.**

- **F-ENV-1 — PaddleOCR requires Python 3.11 + native libraries; it is broken on the default Python-3.13 venv.** (F-3, A-7.)
  - **Why required:** OCR is the entire scanned-PDF and footing-LF capability.
  - **What depends on it:** `ocr.py` (LF extraction, hardware counting, scanned schedule OCR→text) and therefore foundation quantities and scanned-PDF specs.
  - **System deps:** `libgomp1`, `libgl1` (provided in the Docker image per `TODO.md`); on the host they are **not** to be installed (constraint). PaddlePaddle pin **3.2.0** (3.3.x incompatible), PaddleOCR **3.3.0**, Python **3.11** only.
  - **Alternative:** run only inside the existing Docker image (the canonical path) — **recommended**; do not attempt host-level installs.
  - **Needed for:** development, testing, AND production (it's a core runtime dependency).
- **F-ENV-2 — `tesseract` binary is referenced but not installed on the host** (memory). Not currently used by the shipped path; only relevant if a tesseract fallback is ever pursued. *Do not install at OS level* — document as a dependency if that route is chosen.
- **F-ENV-3 — Two committed venvs in the working tree** (`venv/melvin`, `venv/melvin311`) + `app/backend/venv`. *Impact:* tree bloat and ambiguity about which interpreter is "the" one (A-7). *Recommendation (not actioned):* gitignore venvs; document the one canonical interpreter per task.
- **F-ENV-4 — Canonical run is Docker Compose** (`app/docker-compose.yml`, ports backend 8037 / frontend 3036 / postgres). Reuse it; no new environments. (I did not start containers this session.)

---

## G. Blockers preventing confidence in implementation

1. **No reproducible baseline** (F-4) — cannot prove current quality or detect regressions. *Highest-priority unblock:* C-R1.
2. **Current-code behavior unverified** — the JSON artifacts are stale; a captured Docker run is needed to confirm which findings are already fixed vs still live. Specifically re-verify: SVR architect/sqft, Rule-5 flagging, Paseo OCR, LHERT LF/concrete, noise in `raw_json`.
3. **Scope undecided** (Q-1) — the central requirement (quantities) is unmeetable as built; without a scope decision, "what done looks like" is undefined. *Unblock by default decision* (C-R2) since the client is silent.
4. **Production gated by Gemini quota** (F-5/D-2) — real usage impossible until resolved.
5. **Client feedback loop is broken** (`client_responsiveness`) — validation of accuracy/format/priorities cannot come from Melvin; must proceed on documented defaults.

---

## H. Suggested sequence to regain confidence (analysis conclusion, not an instruction to act)

1. **C-R1** capture a baseline (Docker) → makes everything else measurable.
2. **C-R4** security hardening + key rotation → the app is live and exposed today.
3. **C-R3** enforce Rule-5 provenance/flagging → stop shipping confidently-wrong numbers.
4. **C-R2 / C-R9** write the scope decision + reconcile the spec → restore docs as source of truth.
5. Only then weigh additive work (C-R5/7/8) — and treat Path B (C-R10) as a procurement decision, deferred until a client commits to needing it.
