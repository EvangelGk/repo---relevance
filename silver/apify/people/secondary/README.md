# apify/people/secondary

Real, runnable functions derived from Apify LinkedIn person data, one
function per file under `datapoints/`. None of these are wired into a
live pipeline yet - `silver/people/connector.py` references them, but
nothing calls that connector for real. Each module has its own test in
`tests/` exercised with representative sample data.

| Module | Function | Note |
|---|---|---|
| `datapoints/experience_array_resolve.py` | `function_experience_array_resolve` | Normalizes a raw work-history array; also computes `total_years_experience`/`current_tenure_years` - see docstring for why this absorbs the "years of experience" concept instead of `experience_signal_extract` getting a duplicate people-side clone (Task 4 decision below). Also the source `silver/people/connector.py` derives `employed_company` from (current-entry `company` string, not a resolved `company_id` - see connector docstring). |
| `datapoints/connections_band.py` | `function_connections_band` | LinkedIn's own UI band: exact count under 500, `"500+"` at/over |
| `datapoints/mutual_connections_context.py` | `function_mutual_connections_context` | Summarizes a mutual-connections list/count into `{mutual_count, sample_names}` |
| `datapoints/engagement_aggregate.py` | `function_engagement_aggregate` | Aggregates a list of post engagement dicts into totals/averages |
| `datapoints/topic_classify.py` | `function_topic_classify` | Keyword/alias matching against a fixed topic taxonomy - same pattern as Firecrawl's `compliance_framework_extract` |
| `datapoints/bio_entity_extract.py` | `function_bio_entity_extract` | Regex entity extraction (URLs, `at <Company>`, `@<Handle>`) from bio/about free text |
| `datapoints/fund_role_normalize.py` | `function_fund_role_normalize` | VC/PE-specific title vocabulary - deliberately NOT the same enum as `function_seniority` |
| `datapoints/person_certifications.py` | `function_person_certifications` | People-side analog of Firecrawl's `compliance_framework_extract` - see its own docstring |

**`seniority.py` moved to `apify/people/universal/datapoints/` on
2026-09-09** - see that module's docstring and `universal/README.md` for
why: "universal" was redefined from "raw-field extractor" to "a field
present on every person record regardless of source shape," which
`seniority` (always derivable once `job_title` is non-empty) qualifies
for even though it's still a derived, not raw, value.

## Task 4 decisions (recorded here, not in a separate migration doc)

1. **`compliance_framework_extract` -> `person_certifications.py`.** Built
   as a fresh, separate function (Firecrawl never sees person data in this
   repo, so the Firecrawl file itself was never touched or copied) sourced
   from Apify's LinkedIn "Certifications and Dates" array. Exact Apify key
   name is unconfirmed - the function accepts several plausible key-name
   shapes rather than guessing one; see its docstring.
2. **`experience_signal_extract`** (reads company founding-year/tenure
   *claims* out of marketing prose) does **not** get a separate people-side
   clone. Its underlying concept already has a people-side home:
   `function_experience_array_resolve` computes `total_years_experience`
   and `current_tenure_years` directly from a person's structured work
   history, strictly better evidence than regex-scanning prose. Building a
   second function would just be `experience_array_resolve` with extra
   steps.
3. **`service_region_extract`** - no action, no build. A person doesn't
   have "service regions"; no analogous people-side concept to capture.
