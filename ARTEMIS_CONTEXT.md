# Artemis context (distilled brief, for this repo only)

Distilled from the `gtm-core` monorepo's Artemis/Hermes docs
(`artemis-hermes-orchestration-strategy.md`,
`artemis-orchestrator-evaluation.md`, `artemis-orchestrator-proposal.md`,
`Larridin GTM Thesis.md`) as of 2026-09-07, via a separate Cowork session -
not generated from this repo's own code. This repo has no live connection
to that monorepo; treat this as a snapshot, not a synced source.

## What Artemis is

Artemis is the list-building + deterministic-context production line -
"Tier 0-2" in the Larridin reference pattern. Charter (verbatim, from that
monorepo's `service-ops/products/artemis/README.md`): Artemis is **the
production line that feeds every execution product** (Hermes today; Argos
and, Stage 2, Atlas/Iris later).

## Where it stands today (in that monorepo, not here)

- **Zero canonical code** across any of that monorepo's 6 client repos -
  100% manual work in Clay, by one human, one client at a time.
- The manual process is a 9-step checklist: interpret brief -> choose path
  -> pull from source -> ingest -> **clean/dedupe** -> **enrich
  waterfalls** -> apply gates -> suppress against DNC -> hand off.
- DNC suppression happens at step 8, by hand, inside the same workflow -
  not a pre-check.
- An orchestrator/skill split is **approved in principle** (per the v2
  proposal's evaluation) but still being built out - some pieces
  (a shared quota/DNC ledger in Supabase, the `manage-nodes` taxonomy-mint
  gate) are explicitly sequenced behind an admin-answered question and
  aren't finished yet.

## Where THIS REPO fits

This repo started (2026-09-07) as a prototype of just the
**clean/dedupe** and **enrich waterfalls** steps (steps 5-6 of 9) via
`silver/firecrawl/` + `silver/silver_orchestrator/` - take a company
page's markdown, extract structured datapoints, gate the result on
quality before it's usable downstream. Scope has since expanded
(2026-09-08, at explicit user direction, not silent drift) to also
prototype step 1 ("interpret brief") and step 3 ("pull from source") -
see "Scope expansion" below. None of it is wired into Clay or the real
Artemis flow today, and none of it is, itself, the Artemis orchestrator.

`SilverOrchestrator` here mirrors the *shape* of the approved
orchestrator/skill split (a policy layer in front of pure execution) but
is scoped to this repo only:

| Concept | The (future, monorepo-side) Artemis orchestrator | This repo's `SilverOrchestrator` |
|---|---|---|
| Owns | quota, DNC, compliance, cross-client state | contracts, schema gate, quality score, drift, dead-letter - Silver layer only |
| Shared state | Supabase (cross-client ledger) | local JSONL files (`dead_letter.jsonl`, `quality_history.jsonl`) |
| Decides | when to call the execution skill at all | pass/reject on a single extracted row |

## Scope expansion since the original prototype (2026-09-08 additions)

All added at explicit user direction while exploring vendor public APIs
from the terminal - not silent scope drift. See `CLAUDE.md`'s dated
addition notes for the full reasoning behind each:

- **`client_context/`** - Artemis step 1 (interpret brief). A frozen
  `ClientContext` dataclass (interpreted ICP) loaded from one JSON file
  per client.
- **`bronze/clay/`** - Artemis step 3 (pull from source) for companies.
  Builds a Clay search-query-language string from a `ClientContext` and
  runs Clay's public company-search API. Confirmed live against real
  companies, not just unit-tested.
- **`bronze/firecrawl/`, `bronze/apify/`, `bronze/prospeo/`** -
  placeholders: direct, single-vendor API calls (no Clay relay - see
  `CLAUDE.md`'s 2026-09-08 notes for why Clay's column-size ceiling made
  a relay a bad fit for these three). None are called from anywhere else
  in this repo yet.
- **`silver/apify/company/` and `silver/apify/people/`** - Apify-sourced
  datapoint extraction, parallel in spirit to `silver/firecrawl/` but a
  simpler plain-function pattern (`universal/` = raw-field extractors or,
  since 2026-09-09, any field present on every record regardless of
  source shape; `secondary/` = genuinely derived/computed functions).
- **`silver/prospeo/people/`** - Prospeo-sourced people fields; currently
  a docstring-only loader stub, no parsing logic yet.
- **`silver/company/connector.py` and `silver/people/connector.py`** -
  assemble one company/person row across Apify + Firecrawl (+ Prospeo for
  people), each gated through `silver_orchestrator`'s generalized
  `build_function_report()` / `evaluate_record()` helpers -
  `SilverOrchestrator.process_page()`/`process_batch()` themselves remain
  Firecrawl-only; these connectors call the generalized helpers directly.
- **`silver/foreman/`** - resolves a field when two sources disagree
  (e.g. Apify vs. Firecrawl on company name), rather than one source
  silently winning by call order.

**Still true as of 2026-09-09, confirmed by direct grep**: `bronze/` and
`silver/` are not imported into each other anywhere
(`grep -rn "from bronze\|import bronze" silver app.py` = 0 hits). Every
module above is independently tested; there is no live end-to-end
pipeline yet. Don't describe one as existing.

## Explicitly OUT of scope in this repo (on purpose)

- No quota tracking, no DNC suppression, no Supabase-backed shared ledger.
- No `manage-nodes`-style HITL taxonomy-mint gate.
- No run/batch idempotency keys tied to a cross-client system.
These belong to the full Artemis orchestrator once the admin-answered
question (DNC ownership) and `manage-nodes` are further along. Building
them here now would mean re-doing them against a design that isn't final
yet - see the Cowork Project's `claude/repo-relevance-orientation-brief.md`
for the fuller reasoning if it's been written by the time you read this.

## Named requirements to stay compatible with (not build yet)

If/when this repo's output starts feeding the real Artemis flow, it should
already produce data compatible with: a run/batch ID per invocation (for
idempotency), a quality/staleness signal a go/no-go gate can read (this
repo's `quality_score` is a candidate), and the two named Observability
signals from that monorepo - "DNC compliance failures" and "list-to-send
conversion" (neither is this repo's job to emit, but its output shouldn't
make them harder to compute later).
