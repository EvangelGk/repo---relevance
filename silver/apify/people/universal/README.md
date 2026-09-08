# apify/people/universal

Real, runnable code: one extractor per field under `datapoints/`
(`linkedin_url.py`, `full_name.py`, `job_title.py`, `country.py`,
`linkedin_about.py`), mirroring `firecrawl/datapoints/`'s one-function-
per-file convention. `extract.py`'s `extract_person_universal_fields` is
a thin composition, not a datapoint itself - it just calls each of the
five and assembles the flat dict `silver/people/connector.py` consumes.
`<field>_source` tags are stamped by the connector, not by this module.

**`seniority` and `employed_company` are deliberately excluded from this
module** - despite being listed as "universal" fields in the original
plan, neither is a raw Apify field. `seniority` needs deriving from
`job_title` (`apify/people/secondary/datapoints/seniority.py`);
`employed_company` needs resolving out of the full experience array
(`apify/people/secondary/datapoints/experience_array_resolve.py`). Both
are handled inside `silver/people/connector.py` instead - see its
docstring.

No live Apify integration exists yet anywhere in this repo. Field-name
maps assume common Apify LinkedIn person-actor conventions; confirm
against a real sample before production use.
