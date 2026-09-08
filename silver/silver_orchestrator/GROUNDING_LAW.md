# Grounding Law

Adapted from a B2B account-research crawl-extraction prompt (Cowork
Project schema-inspiration proposal, 2026-09-07) into this repo's actual
inputs and outputs. Rules 1, 2, and 4 (grounding discipline, no
cross-field fabrication, no placeholder strings) bind every datapoint
function in `silver/firecrawl/datapoints/` AND every extractor in
`silver/apify/company/universal/datapoints/` and
`silver/apify/people/universal/datapoints/` (added 2026-09-08, when those
became the second and third sources this orchestrator actually gates -
see `contracts.APIFY_COMPANY_CONTRACTS`/`APIFY_PEOPLE_CONTRACTS`). Rule 5
stays scoped to `silver_orchestrator/triage.py` and Firecrawl specifically
- see below for why.

1. Every value a function reports must be reconstructible from the
   `markdown` and `context` it was actually given - never from prior
   knowledge of the company, never invented to fill a gap.
2. No function may derive a company fact (industry, location, market,
   language) from another field's *name* or *shape* alone - e.g.
   `domain_normalize`'s output is a join key, not evidence for
   `service_region_extract`'s country guess. Cross-function reasoning
   belongs to `company_entity_resolve` and `conflict_check.py` only, and
   only for the specific fields their own docstrings name.
3. Never infer a company's country, market, or language from a domain
   string, a TLD, or the page's own detected language
   (`site_locale_detect`'s output). A `.de` domain or a German-language
   page is not evidence of German customers - `service_region_extract`
   must find an explicit place-name span, not guess one.
4. "Nothing found" is reported as `None`/`[]`/`{}` (see
   `Firecrawl._collapse_if_blank`), never as a placeholder string
   ("N/A", "Unknown", "Not specified").
   `schema_gate._check_no_placeholder_strings` is the automated backstop
   for this rule - it is a backstop, not a substitute for writing
   extractors that already follow it.
5. `triage.classify_crawl_issue` and `triage.classify_content_integrity`
   read only `markdown` - not a domain, not a URL, not any other
   out-of-band signal. Rule 3 applies to them exactly as it applies to
   the datapoint functions. Scoped to Firecrawl only: triage is a "was
   this scraped page even usable" gate, and an Apify/Prospeo record is
   already a structured object with no such question to ask - see
   `triage.py`'s own module docstring.

Fewer defensible values beat more plausible ones. When a function is torn
between reporting a weak guess and reporting nothing, `null_tolerance_pct`
in `contracts.py` already prices in "nothing" as the expected, non-
penalized outcome for most functions in each contracts dict - see
`/review-contract`. (The count of functions this covers isn't fixed - read
it off whichever contracts dict applies, `contracts.py`, not a memorized
number; it has changed before and will again.)
