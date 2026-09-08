# apify/company/universal

Real, runnable code: one extractor per field under `datapoints/`
(`name.py`, `industry.py`, `headcount.py`, `location.py`,
`linkedin_url.py`), mirroring `firecrawl/datapoints/`'s one-function-per-
file convention. `extract.py`'s `extract_company_universal_fields` is a
thin composition, not a datapoint itself - it just calls each of the five
and assembles the flat dict `silver/company/connector.py` consumes.
`<field>_source` tags are stamped by the connector, not by this module.

No live Apify integration exists yet anywhere in this repo (`silver/apify/`
was documented in `CLAUDE.md` as "empty, future source"), so there is no
confirmed real sample to build against - each datapoint's multi-key
fallback assumes common Apify LinkedIn company-actor field names and is
designed so remapping is a one-line change once a real sample exists, not
a rewrite. See each module's own docstring.

`location` lives here (not a `reconciled/` merge) - no live Firecrawl
extractor produces a location/HQ signal at all (`structured_data_extract`
was removed; cleaned markdown can't preserve schema.org JSON-LD), so
Apify is the only real source and there's nothing to reconcile.

Two other company join-key fields are **not** duplicated here even though
they are logically "universal": `domain` and `linkedin_url`.
- `domain` - `silver/firecrawl/datapoints/domain_normalize.py` (required
  field, `context["source_url"]`-only since the 2026-09-08 bug fix) - the
  `company/` connector reads it from `firecrawl_row` directly.
- `linkedin_url` - genuinely Apify-sourced like the rest of this module's
  fields, and IS produced here (`datapoints/linkedin_url.py`).
