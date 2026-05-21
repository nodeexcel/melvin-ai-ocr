## Core Rules

**1. Don't assume — ask**
If anything is unclear or ambiguous, stop and ask. Don't fill in gaps with guesses.

**2. Always verify with research**
For library versions, API signatures, model names, or any external fact — look it up before using it. Training data goes stale.

**3. Surface better approaches**
If there's a better way to build something, say so before writing a line of code. Discussion is cheap; rewrites are not.

**4. Pipeline changes require a test run**
Any change to extraction prompts, title block patterns, routing logic, or output schema must be validated against at least one of the 6 test PDFs before being considered done. Don't declare a fix done without a real run — silent regressions are easy to introduce.

**5. Never return unverified quantities**
If Vision estimates a number from a graphical drawing (concrete CY, linear feet, piece counts), flag it as `estimated: true` in the output — never return it as a confirmed measurement. The client uses these numbers for real ordering. Unmarked estimates cause ordering errors.

**6. Schema changes cascade**
If `analysis_results.raw_json` structure changes, the PDF report template and frontend results page both need to change at the same time. Never change the schema in isolation.

**7. Docs are the source of truth**
`docs/pipeline-findings.md` = pipeline behavior and test results. `TODO.md` = project state. Keep both current after every significant change. If state lives only in conversation history, it will be lost on the next context reset.
