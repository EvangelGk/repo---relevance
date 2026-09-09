# apify/people/universal

Real, runnable code: one extractor per field under `datapoints/`
(`linkedin_url.py`, `full_name.py`, `job_title.py`, `seniority.py`,
`country.py`, `linkedin_about.py`, `age.py`, `company_industry.py`),
mirroring `firecrawl/datapoints/`'s one-function-per-file convention.
`extract.py`'s `extract_person_universal_fields` is a thin composition,
not a datapoint itself - it just calls each extractor and assembles the
flat dict `silver/people/connector.py` consumes. `<field>_source` tags
are stamped by the connector, not by this module.

**What "universal" means here was redefined on 2026-09-09** (at explicit
user direction): it no longer means strictly "a raw-field extractor off
the Apify record." It now means "a field present on every person record
regardless of source shape." `seniority` moved here from `secondary/`
under that redefinition - it's still derived (from `job_title`, via a
keyword ladder in `seniority.py`), not a flat passthrough, but every
LinkedIn profile has *some* title to derive it from, so it's as
universally available as any raw field.

`employed_company` is still excluded, and still belongs in the
"deliberately not raw, and not universal either" bucket: unlike
`seniority`, it needs resolving the current entry out of a full,
possibly-absent experience array
(`apify/people/secondary/datapoints/experience_array_resolve.py`), not a
transform of one always-present scalar. It's handled inside
`silver/people/connector.py` instead - see its docstring.

`age` and `company_industry` (added 2026-09-09) are back to being plain
raw-field extractors, same shape as `country`/`job_title` - see each
module's own docstring for source-field caveats (`age` in particular:
LinkedIn doesn't publicly expose birthdate/age at all, so expect `None`
on most real profiles).

No live Apify integration exists yet anywhere in this repo. Field-name
maps assume common Apify LinkedIn person-actor conventions; confirm
against a real sample before production use.
