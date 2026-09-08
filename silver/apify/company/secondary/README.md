# apify/company/secondary

New-build functions, derived from `apify/company/universal/` fields. Real,
runnable implementations, one function per file under `datapoints/` -
each module's docstring documents its input contract and which
assumptions are grounded (e.g. LinkedIn's own public company-size/
company-type taxonomies) vs. which are a documented heuristic pending a
real Apify sample to confirm exact field names against (`hiring_signal`).

`founded_year_reconcile.py` (LinkedIn/Firecrawl/CrunchBase 3-way
reconciliation, chaining a foreman function twice) and the foreman itself
(`function_source_priority_resolve`) were both built at one point, then
deliberately deleted - not enough real datapoint value to justify a
reconciliation mechanism for a single field with no other multi-source
consumer yet. Revisit if/when a second genuinely multi-source field shows
up.

| Module | Function | Depends on |
|---|---|---|
| `datapoints/headcount_band.py` | `function_headcount_band` | `apify/company/universal.headcount` |
| `datapoints/hiring_signal.py` | `function_hiring_signal` | Apify LinkedIn job-postings signal (exact field name TBD, see module docstring) |
| `datapoints/company_type_normalize.py` | `function_company_type_normalize` | Apify LinkedIn company-type field |

Each has a matching test in `tests/` run with sample data (no live Apify
pull needed to sanity-check the logic).
