---
name: review-contract
description: Checklist for adding or changing a DatapointContract entry in silver_orchestrator/contracts.py so required/null_tolerance_pct/source_priority/enum_values stay evidence-based and consistent with schema_gate.py and quality_score.py.
---

# Reviewing a `DatapointContract` change

Before merging a change to `silver/silver_orchestrator/contracts.py`,
check each of these:

## 1. `required=True` is reserved for join-key-critical fields

Today that's only `domain_normalize` and `company_entity_resolve`
(specifically its `company_id` sub-field - see `schema_gate.py`'s
`_has_company_id`, which checks that key, not the whole dict). Don't flip a
function to required just because it's useful or usually populated - most
of the datapoint functions are *legitimately* empty on plenty of real
pages, and marking one required turns a normal empty result into a
rejected row.

## 2. `null_tolerance_pct` is justified, not guessed

It should reflect how often the signal is genuinely absent on a real page
sample, not a round number picked for symmetry:
- High tolerance (70-80%+) for narrow/niche signals - careers pages,
  pricing pages, regulatory events. Most B2B pages simply don't have these.
- Low tolerance (10-20%) for near-universal signals - a resolvable domain,
  a footer with a copyright line.
Leave a trailing comment explaining the number, matching the existing
entries' style, so the next person doesn't have to guess whether it was
measured or invented.

## 3. `source_priority` is ordered best-to-worst and complete

It must match exactly the vocabulary of `self._last_source` values that
function's `extract()` can actually set - go check the datapoint file,
don't assume from the name. `quality_score.compute_quality_score`
penalizes any run that used something other than `source_priority[0]`, so
a wrong or incomplete order silently mis-scores every row that used a
source further down the list (or not represented at all).

## 4. `enum_values` only for controlled vocabularies

Currently: `regulatory_event_classify` (a flat tuple) and `business_model`
(the one nested exception - a tuple of three tuples in `(pricing, offering,
delivery)` order; read the `DatapointContract` dataclass docstring before
copying that shape elsewhere). Don't add `enum_values` to a free-text or
open-ended field.

## 5. Contract changes that affect validation logic need matching code changes

A number-only tweak (e.g. adjusting `null_tolerance_pct`) is contracts.py
in isolation. A new *kind* of constraint (e.g. "this field must also be a
valid ISO date") needs a corresponding check added to `schema_gate.py`'s
`evaluate_row` - `/add-orchestrator-check` walks through that.

## 6. Verify

```
poetry run pytest silver/silver_orchestrator -q
```

The existing tests exercise `evaluate_row` and `compute_quality_score`
against real sample data (`silver/firecrawl/tests/sample_input.md`) and
will catch a contract that's now too strict (rejecting a previously-valid
sample row) or too lenient (silently accepting a case it shouldn't).
