---
name: add-orchestrator-check
description: Scaffold a new hard-requirement, quality-score penalty, or drift rule consistently across contracts.py, schema_gate.py, quality_score.py, drift.py and their tests, so the files don't drift out of sync.
---

# Adding a new orchestrator-level check

A "check" in this pipeline is one of three distinct things - decide which
one before writing code, since they have very different consequences for a
row:

| Kind | Lives in | Effect on the row |
|---|---|---|
| Hard requirement | `schema_gate.py` | `is_valid_row=False`, goes to `dead_letter.jsonl` |
| Quality penalty | `quality_score.py` | Lowers `quality_score`, row still valid |
| Drift signal | `drift.py` | Appends to `row["drift_warnings"]`, never gates |

Don't reach for a hard requirement when a soft penalty is more honest - most
of the datapoint functions are legitimately empty on real pages (see
`/review-contract`). When in doubt, a quality penalty or drift warning is
the safer default; hard requirements should be rare and deliberate.

## Adding a hard requirement (`schema_gate.py`)

1. If it's just "this required field must be non-empty," check whether
   `evaluate_row`'s existing required-fields loop (driven by
   `contracts.DATAPOINT_CONTRACTS[name].required`) already covers it before
   writing a bespoke check.
2. For a shape/type check on a nested field (the `_check_social_links_shape`
   / `_check_careers_shape` pattern), write a plain Python function
   returning `list[str]` - pandera's `Column` doesn't fit nested dict/list
   values cleanly here (see the module docstring in `schema_gate.py` for
   why: a pandera Check on such a column just receives the whole
   dict/list as one cell, so it buys nothing over a direct function).
3. For a scalar/enum check, add a `Column` to `_ROW_SCHEMA`. **Do not pass
   an explicit `dtype=`** - pandas 3's default string dtype (`str`, not the
   legacy `object`) breaks pandera's dtype check even when the values are
   fine; the `Check` callable is what actually validates here, not the
   declared dtype. Follow the existing Columns' shape.
4. Call your new checker from `evaluate_row` and append its violation
   strings to the returned list.

## Adding a quality penalty (`quality_score.py`)

Add the penalty inside `compute_quality_score`'s loop over
`contracts.items()`, following the existing two penalties' shape
(`_REQUIRED_EMPTY_PENALTY`, `_LOW_PRIORITY_SOURCE_PENALTY`):
- Name the constant, don't inline a magic number.
- Keep it additive off the 100.0 baseline.
- The final `[0, 100]` clip already happens once at the end of the
  function - don't clip inside the loop too.

## Adding a drift signal (`drift.py`)

Per-function, per-page drift tracking already exists
(`DriftTracker.record_run` / `is_drifting`). A genuinely new *kind* of
drift (not just "track this new function too," which needs no code change -
`SilverOrchestrator.process_page` already calls `record_run`/`is_drifting`
for every entry in `function_report`) means extending `DriftTracker`
itself. Keep the invariant from `orchestrator.process_page` intact: drift
only ever appends to `row["drift_warnings"]`, it must never set
`is_valid_row=False` or touch `quality_score`.

## Always, regardless of which kind you added

1. Update `silver/silver_orchestrator/tests/test_silver_orchestrator.py`
   with a case exercising the new check against both a passing and a
   failing input.
2. Run:
   ```
   poetry run pytest silver/ -q
   ```
   before considering it done.
