# silver/foreman

"The foreman" - resolves competing candidate values for one datapoint,
across however many sources actually show up, into one authoritative
value plus its provenance.

## Why this package exists (and why it's back)

A foreman + a `founded_year_reconcile.py` were built once before in this
repo, then deliberately deleted - see
`silver/apify/company/secondary/README.md` and `silver/company/connector.py`'s
docstring, both still on disk and accurate about that history. The reason
given at the time was real: a mechanism for reconciling competing sources
wasn't worth keeping for exactly one field with no second multi-source
consumer.

The design itself was also wrong in a way that mattered more: it took
exactly two positional `(value, source)` pairs and handled a third
candidate (`founded_year` has three: Apify, Firecrawl, CrunchBase) by
chaining two calls together as a workaround. That's arity hardcoded into
the function signature. This package replaces that design, not just
restores it: `function_source_priority_resolve` now takes an arbitrary
list of candidates - 2, 3, or 15 - through one unchanged call shape,
proven in `test_foreman.py` at 2-, 3-, 5-, and 15-source scale.

**Current status: standalone, not wired in.** This drop adds only the
package itself (`source_priority_resolve.py`, `priority_rules.py`,
`test_foreman.py`, this README) under `silver/foreman/`. `company/connector.py`
still does pure static tagging for every field, `founded_year` isn't
assembled or exposed anywhere yet, and neither `connector.py`'s docstring
nor `apify/company/secondary/README.md` has been updated to reflect that
a foreman exists again - both still correctly describe the pre-this-drop
state. Wiring this into `connector.py`, adding a real `founded_year`
candidate to `apify/company/universal/extract.py`, and giving CrunchBase
an actual source folder are separate, later decisions, not part of this
change.

## API

```python
from silver.foreman.source_priority_resolve import function_source_priority_resolve
from silver.foreman.priority_rules import PRIORITY_RULES

result = function_source_priority_resolve(
    candidates=[
        {"source": "apify", "value": apify_founded_year},
        {"source": "firecrawl", "value": firecrawl_row["legal_entity_extract"]["copyright_year"]},
        {"source": "crunchbase", "value": crunchbase_founded_year},
    ],
    priority_rule=PRIORITY_RULES["founded_year"],
)
# {"value": ..., "source": ..., "conflict": bool, "ambiguous": bool,
#  "raw_values": {...every candidate, win or lose...}, "candidate_count": 3}
```

`candidates` - any length, including 0 or 1 (not a real contest in either
case - handled as a passthrough, not an error). Each entry is
`{"source": str, "value": Any}`, with an optional `"meta": {...}` dict for
criteria that need more than the raw value (a timestamp, a confidence
score, a structured-vs-free-text flag).

`priority_rule` - `{"criteria": [...], "normalize": "int" | "lower_strip" | None}`.
`criteria` is an ORDERED list of tie-breakers, walked in sequence until
one narrows the disagreeing candidates to a single winner. Each entry
names a `"type"` from the registry below; a field can chain more than one
when a single rank isn't enough (see the commented template in
`priority_rules.py`).

| Criterion type | Picks the source that... | Reads |
|---|---|---|
| `static_rank` | appears earliest in a fixed `"rank"` list | `spec["rank"]` |
| `prefer_structured` | has `meta[meta_key]` truthy (structured data over free text) | `candidate["meta"]` |
| `most_recent` | has the latest `meta[meta_key]` timestamp | `candidate["meta"]` |
| `highest_confidence` | has the highest `meta[meta_key]` score | `candidate["meta"]` |
| `majority_vote` | has the most candidates agreeing on it | candidate count per value |

A criterion that can't distinguish (no metadata present, or a genuine
tie) abstains and passes the group set to the next criterion unchanged.
If every criterion in the list abstains or ties, the result is flagged
`ambiguous: true` and falls back to the first candidate in call order -
deterministic, never random, and always visible to whoever reads the
result rather than a silent guess.

## `priority_rules.py`

One entry per datapoint that genuinely has 2+ live candidate sources -
not a global source hierarchy. Today that's exactly one field:

```python
"founded_year": {
    "criteria": [{"type": "static_rank", "rank": ["crunchbase", "firecrawl", "apify"]}],
    "normalize": "int",
}
```

Rank order, and why it inverts Apify's usual default-winner status:
CrunchBase is registry-diligenced, closest to a legal fact available to
this pipeline. Firecrawl's candidate (`legal_entity_extract.copyright_year`,
a footer "© 2024 Acme Inc." string) is a real dated value but often marks
a rebrand or site-relaunch year, not the true founding year. Apify's
LinkedIn "founded" field is the weakest of the three specifically here -
company-controlled marketing copy, rarely corrected - even though Apify
is the correct default for nearly every other company/people datapoint in
this repo (see `apify/company/universal/` and `apify/people/universal/`).
That inversion is *why* the priority question lands on Apify at all:
everywhere else it wins without a contest; `founded_year` is the one place
it's usually wrong.

Add a new entry the moment a second field gets a second live source.
Don't pre-populate a rule for a field that only has one source today - a
commented-out template further down `priority_rules.py` shows the shape
for a field that would need to chain two different criterion types.

## Tests

`test_foreman.py` - pytest-native (matches this repo's existing test style,
e.g. `apify/company/secondary/tests/test_headcount_band.py`), run with
`poetry run pytest silver/foreman -q`. 16 test functions: 0/1/2/3-candidate
basics, an explicit 5-source scenario and two 15-source scenarios (only 1
of 15 has data; 3 of 15 disagree and rank among just those 3 decides),
criteria chaining (a `static_rank` tie falling through to `majority_vote`),
`prefer_structured`, `most_recent` with metadata timestamps, the
exhausted-criteria ambiguous fallback, and an explicit `pytest.raises(ValueError)`
on an unregistered criterion type - never a silent wrong answer. All 16
pass as of this drop (verified against the real target import path,
`silver.foreman.*`, before delivery).

## Open, not decided here

- No live source produces a `founded_year` candidate yet on any side:
  `apify/company/universal/extract.py` has no `founded_year` field,
  CrunchBase has no source folder in this repo, and only Firecrawl's
  `legal_entity_extract.copyright_year` is real today. The foreman and
  its config are ready for when those exist - they don't manufacture the
  missing candidates themselves.
- Wiring `founded_year` into `company/connector.py` (and updating that
  file's docstring plus `apify/company/secondary/README.md`, both of
  which still describe the pre-foreman state) is a deliberate next step,
  not part of this change.
