---
name: update-orchestrator
description: Re-checks silver_orchestrator/ (contracts, schema_gate, quality_score, drift, triage, dead_letter) against every current source/connector in the repo, and proposes exactly what's out of sync. Never edits code directly — always produces numbered WHAT/WHY/PROPOSAL/PROS-CONS/ALTERNATIVE proposals and waits for explicit per-item approval. Treat as vital-priority: run this whenever a new source, connector, or datapoint contract is touched.
---

# update-orchestrator

## Why this exists
`silver_orchestrator/` is "the difference between successful results and
logical errors in handling" (repo owner's own framing) — it's the one
package every source funnels through before anything reaches a final
table. It must never silently fall behind when a new source/connector/
datapoint is added. This skill is the dedicated, always-on check for
exactly that package.

## What it checks, every run
1. List every `*_CONTRACTS` dict currently defined in `contracts.py`
   (today: `DATAPOINT_CONTRACTS`, `APIFY_COMPANY_CONTRACTS`,
   `APIFY_PEOPLE_CONTRACTS`).
2. List every source/connector folder that produces a row today
   (`silver/firecrawl/`, `silver/apify/company/`, `silver/apify/people/`,
   `silver/prospeo/people/`, `silver/company/connector.py`,
   `silver/people/connector.py`) and every field each one emits.
3. Diff #1 against #2: any source/connector emitting a field with no
   matching contract entry anywhere is a gap. Any contract entry whose
   source field no longer exists is stale.
4. Re-read `GROUNDING_LAW.md` against every datapoint/extractor
   docstring added since the last run — flag anything that looks like it
   derives a company fact from a domain/TLD/detected language (the one
   hard rule this file exists to enforce).
5. Check `schema_gate.py`'s required-field list and
   `_check_no_placeholder_strings` token list are still accurate against
   what extractors actually return.
6. Check `drift.py`'s tracked functions list covers every current
   datapoint, not just the original Firecrawl set.

## Output format — mandatory, no exceptions
For every gap found, output one numbered block in exactly this shape
(this exact template — the repo owner requires it verbatim):

> **N. WHAT:** <the specific gap, named by file + field>
> **WHY:** <why it matters — what breaks or silently degrades if left>
> **PROPOSAL:** <the concrete change>
> **PROS / CONS:** <bulleted, honest, including the cost of doing it>
> **ALTERNATIVE (2nd proposal):** <a genuinely different approach>
> **PROS / CONS (alternative):** <same rigor>

Then stop and ask: "Which numbers should I apply?" Do not write any code
change until the human answers with specific numbers (or "all").

## Hard rule
This skill never runs `git commit`/`push`/`clean`/`reset --hard` and
never edits a file the human didn't explicitly approve by number in this
same session.
