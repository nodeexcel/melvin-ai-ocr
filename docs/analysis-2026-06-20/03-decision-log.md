# 03 — Decision Log

**Session:** 2026-06-20. Part A = decisions I made *during this analysis* (with reasoning). Part B = project decisions reconstructed from the record, with my assessment. Part C = recommendations for future implementation (analysis-only — these are proposals, not actions), with alternatives compared.

---

## Part A — Decisions taken during this analysis

### A-D1 — Follow the user's 4-document framework over the `product-bde-analyzer` skill
- **Decision:** Structure output as the four requested docs rather than invoke the dual business/technical analysis skill.
- **Reasoning:** The user's framework is more specific and prescriptive (named deliverables, a strict per-PDF review process, environment constraints). A generic skill would produce a different shape. User instructions outrank skill defaults.

### A-D2 — Ground-truth the PDFs with parallel subagents, then verify critical claims myself
- **Decision:** Dispatch one read-only subagent per PDF to review representative pages + cross-check the JSON, then personally `grep`/parse the JSON files to confirm the most consequential contradictions.
- **Reasoning:** ~438 pages of mostly-rendered imagery across six 7–216 MB files is too token-heavy to read whole. Representative-page review (cover + structural sheets + one plan) answers the requirement questions at a fraction of the cost. Subagent context stays isolated; only conclusions return. But subagent summaries can drift, so I independently verified the claims that drive findings (estimated-flag count, LF/concrete zeros, empty project block, OCR errors, lingering noise codes).
- **Alternative rejected:** Reading every page myself — wasteful, and the user explicitly warned against consuming tokens unnecessarily.

### A-D3 — Treat committed JSON outputs as dated artifacts, not a baseline
- **Decision:** Anchor findings to "this artifact, dated X, shows Y," and separately mark whether the defect likely persists in current code.
- **Reasoning:** The files span 2026-05-25 → 06-18 across different code/environments (verified via timestamps + content). Asserting "the code does X" from a stale JSON would be inaccurate. This caution is itself how I discovered F-4 (no reproducible baseline).

### A-D4 — Do not run the pipeline
- **Decision:** No execution this session.
- **Reasoning:** (1) Analysis-only mandate; (2) it spends the developer's own API budget; (3) it would fail locally anyway — PaddleOCR crashes on the Python-3.13 venv and the working path is Docker-only, which I should not stand up/modify under the environment constraints. Consequence: current-code behavior is asserted only where static evidence supports it; the rest is flagged for verification (`04`).

### A-D5 — Keep filesystem operations tightly scoped
- **Decision:** No home-wide `find`, no Docker calls; used dedicated Read + narrowly-scoped, clearly-read-only shell only.
- **Reasoning:** An earlier broad `find /home` + `docker ps` batch was rejected, and `user_preferences.md` records "does not want unnecessary file browsing." Respecting that.

### A-D6 — Write the new `client_responsiveness` memory (prior session) and let it shape priorities here
- **Decision:** Factor the unresponsive-client + self-funded-API reality into all recommendations.
- **Reasoning:** It changes the optimal posture from "build toward the spec" to "stabilize and de-risk." See D-7.

---

## Part B — Reconstructed project decisions (with assessment)

### B-D1 — Vision-first classification (replaced per-firm regex patterns), 2026-05-25
- **What/why:** Every page classified via GPT-4o-mini thumbnails; hardcoded title-block patterns deleted. Driven by the correct insight (memory `feedback_no_patches`) that per-firm regex breaks on every new firm.
- **Assessment:** ✅ **Sound, root-cause decision.** The right call and consistent with the no-patches principle. (Caveat: the *hardware noise filter* then re-introduced exactly the denylist-of-patterns anti-pattern this decision rejected — see F-8.)

### B-D2 — GPT-4o + Gemini 2.5-flash instead of the spec's Claude Sonnet
- **What/why:** Implementation diverged from the design spec's stated model with no recorded decision.
- **Assessment:** ⚠️ The choice may be fine on merits (Gemini benched well on drawings per `research-extraction-approaches.md`), but it's an **undocumented spec drift** (F-11). Worth a one-line ADR. Note the project advertises itself ("Codebase knowledge: latest Claude models") yet uses OpenAI+Google for the core task — a coherent rationale should be written down.

### B-D3 — PyMuPDF vector extraction for footing LF — researched, tried, abandoned
- **What/why:** `research-extraction-approaches.md` (2026-05-21) called PyMuPDF vector extraction the "biggest quick win" (~90%). Investigation (2026-06-09) found Whaleon p68 had 30k+ stroke paths, all black, dimension text not in the layer → **not viable** without DXF.
- **Assessment:** ✅ **Correct to abandon**, and a good example of validating before committing. Documents that the optimistic research estimate didn't survive contact with the real CAD PDFs — relevant when weighing the *next* optimistic estimate (schedule-OCR, F-13).

### B-D4 — Path C (estimate quantities + flag) adopted implicitly
- **What/why:** quantities.py + waste + cost were built (a hybrid "best-effort estimate" path) although the Path-A/B/C scope fork in findings-and-feasibility §8 was never decided with the client.
- **Assessment:** ⚠️ **A scope-defining decision made by default.** Defensible given the unresponsive client, but it should be made *explicit and documented* — and it raises the Rule-5 stakes (F-2): the moment you ship estimates, flagging them becomes mandatory, and that flagging is currently inconsistent/absent.

### B-D5 — OCR→text for scanned schedules ("Gap 1 resolved")
- **What/why:** Route scanned schedule pages through PaddleOCR→GPT-4o text.
- **Assessment:** ⚠️ **Conceptually right, but "resolved" overstates it.** The capability works only in Docker/Py-3.11; the committed Paseo artifact shows it failing (F-3). Status should read "works in Docker; broken on Py-3.13; not captured to a baseline" until a captured run proves it.

### B-D6 — Single-pipeline codebase (scripts import from `app.pipeline`)
- **Assessment:** ✅ Good — eliminates script/web-app drift. Consistent with quality-over-speed.

---

## Part C — Recommendations for future implementation (proposals only)

Ordered by leverage given the unresponsive-client, self-funded reality. **None implemented this session.**

### C-R1 — Re-establish a reproducible baseline first (precondition for everything)
- **Why:** Without it (F-4), no later change can be proven to help. You're optimizing blind.
- **Proposal:** One captured, dated run of all 6 PDFs in the **canonical Docker environment**, with a written run-manifest (code commit, model versions, env) saved next to each JSON. Make this the regression baseline.
- **Alternatives:** (a) golden-file tests in `tests/` asserting key fields per PDF — more durable but more setup; (b) do nothing — rejected, leaves the project unfalsifiable.

### C-R2 — Make the scope fork an explicit, documented decision (don't wait for Melvin)
- **Why:** F-9 + B-D4. The client won't answer; a default must be chosen and recorded.
- **Proposal:** Formally adopt **Path C (estimate + flag)** as the shipped contract, *plus* commit to **Path A honesty**: anything not read directly off the document is labeled estimated, with the basis shown. Document the six unanswered client questions as "decided by default: …".
- **Alternatives:** Path A only (drop estimates) — simpler, more honest, less "wow"; Path B (geometry) — see C-R5, high cost/risk, do not start speculatively.

### C-R3 — Enforce Rule 5 at the data layer (highest trust-per-effort)
- **Why:** F-2 is the most dangerous defect — confidently wrong numbers.
- **Proposal:** In aggregate.py, every numeric quantity carries provenance (`source: read|schedule|estimated|ocr`) and `estimated: true` unless read directly. Reject/clamp implausible values (negative, zero-from-default). Suppress fabricated Vision hardware (require a model match against an allowlist).
- **Alternatives:** Filter only at render (status quo) — rejected (F-8: stored data stays wrong, other consumers see it).

### C-R4 — Security hardening before any further sharing of the live URL
- **Proposal:** Lock CORS to the known origin (drop `*`+credentials); move SSE auth off the query string; add an upload size cap; add basic login rate-limiting; put TLS in front; rotate the chat-exposed API keys; change the default invite code.
- **Effort:** ~1 day. **Alternative:** take the public instance down until hardened — safest if no one is actively testing.

### C-R5 — Replace the hardware denylist with a Simpson model allowlist
- **Why:** F-8 — the denylist grows forever and re-introduces the anti-pattern B-D1 rejected.
- **Proposal:** Validate hardware against a positive Simpson catalog pattern/list (HDU/HUC/LUS/CMST/A35/ABU/…); everything else is dropped or quarantined. Apply in aggregate.py.
- **Alternative:** keep extending the denylist — rejected on the project's own no-patches principle.

### C-R6 — Resolve the Gemini quota before declaring "production-ready"
- **Proposal:** Paid Gemini tier (a billing/ownership decision, `04` Q-5), or reduce Gemini calls per run, or batch pages. Until then, label the app "pilot, 1 PDF/day."

### C-R7 — Add project-type & completeness detection (cheap trust win)
- **Proposal:** Detect DD/"NOT FOR CONSTRUCTION"/no-S-sheets and steel-MF vs wood; return an explanatory status instead of silent-empty or fabricated output (F-10, F-14).

### C-R8 — Validate the schedule-OCR premise per firm before investing (F-13)
- **Proposal:** Before building the Priority-1 schedule parser, confirm on 2–3 real sets whether schedules actually carry a quantity column. The gold standard does not.

### C-R9 — Reconcile the design spec with reality, or retire it (F-11)
- **Proposal:** Update the spec's model/stack/timing/schema to match the build, or mark it "historical" and point to a current architecture doc. Per CLAUDE.md Rule 7.

### C-R10 — If quantity takeoff is ever pursued (Path B), buy accuracy, don't engineer it
- **Why:** B-D3 shows in-house geometry extraction failed on these CAD PDFs.
- **Proposal (do NOT start speculatively):** the realistic routes are **DXF/CAD files from the engineer** (near-perfect, needs cooperation) or a **specialist service** (iBeam AI, $150–500/job, 90–98%). Both are procurement/relationship decisions, not coding tasks. Defer until a client actually commits to needing it.
