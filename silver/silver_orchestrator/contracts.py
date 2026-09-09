"""Single source of truth for what each datapoint function across silver/
is contractually expected to produce - mirrors the finance project's
SeriesContract/SourceContract pattern: frozen dataclasses instead of magic
numbers scattered across schema_gate.py, quality_score.py, and drift.py.

Three contract dicts live here, one per source that has real, working
extraction code today:

- DATAPOINT_CONTRACTS - Firecrawl's, the original set, still the default
  everywhere a `contracts` parameter is optional.
- APIFY_COMPANY_CONTRACTS / APIFY_PEOPLE_CONTRACTS - added 2026-09-08 for
  `apify/company/universal` and `apify/people/universal`, whose
  extract_*_universal_fields() functions produce a real flat dict today.

Deliberately NOT covered here (as of 2026-09-08): silver/prospeo/ (a
docstring-only loader stub, no parsing logic yet, join key undecided) and
silver/apify/*/secondary/ (no extract.py/runner exists for either side -
just individual functions with documented-unconfirmed field names, e.g.
hiring_signal.py). Writing contracts for fields nothing actually extracts
yet would be guessing shapes the same way this repo has explicitly refused
to elsewhere - add contracts here once each has real output to gate.

Trimmed 2026-09-08 from the original 17-plus-company_description_extract
set down to this list: structured_data_extract (needed JSON-LD that
cleaned markdown never preserves), regulatory_event_classify (near-zero
hit rate outside regulated industries), timeseries_snapshot and freshness
(both depended on inputs - structured_data's employee count, a
re-enrichment history DB - that don't exist in this pipeline yet) were all
removed rather than kept as permanently-empty columns. See datapoints/
docstrings for the per-function reasoning.

null_tolerance_pct and required were set from the 50-doc sample referenced
in the schema-expansion round: most B2B company pages simply don't publish
a careers page or a pricing page, so penalizing those as heavily as a
missing domain would be wrong. required=True is reserved for the two
functions the rest of the pipeline can't join on without: domain_normalize
(the cross-source join key) and company_entity_resolve's company_id
sub-field (the canonical entity key) - see schema_gate.py for why
company_id is checked specifically rather than the whole
company_entity_resolve dict.
"""
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class DatapointContract:
    required: bool
    null_tolerance_pct: float
    # Ordered best-to-worst source labels this function can report via
    # Firecrawl's function_report[name]["source"]. The first entry is the
    # "best available" source; quality_score.py penalizes a function that
    # ran on anything lower in this tuple.
    source_priority: Tuple[str, ...]
    # None for most functions. For regulatory_event_classify this is a flat
    # tuple of allowed values. business_model is the one nested exception:
    # its value is {pricing, offering, delivery}, so its enum_values is a
    # tuple of three tuples in that fixed order (pricing, offering,
    # delivery) rather than one flat tuple - schema_gate.py knows to
    # unpack it positionally for that one function only.
    enum_values: Optional[Tuple] = None


DATAPOINT_CONTRACTS: Dict[str, DatapointContract] = {
    "domain_normalize": DatapointContract(
        required=True,
        # context-only since 2026-09-08 (the markdown-link-guessing fallback
        # was removed for being actively wrong, not just empty - see the
        # datapoint's own docstring). Tolerance stays low: whatever pipeline
        # calls Firecrawl always knows the URL it just scraped, so a missing
        # context["source_url"] is a caller bug, not something to tolerate.
        null_tolerance_pct=10.0,
        source_priority=("context",),
    ),
    "social_links_extract": DatapointContract(
        required=False,
        null_tolerance_pct=30.0,  # most footers link at least one social/review profile
        source_priority=("markdown",),
    ),
    "legal_entity_extract": DatapointContract(
        required=False,
        null_tolerance_pct=15.0,  # almost every page has a copyright footer
        source_priority=("markdown",),
    ),
    "company_description_extract": DatapointContract(
        required=False,
        null_tolerance_pct=20.0,  # most pages open with some descriptive prose, but not all
        source_priority=("context", "markdown"),
    ),
    "site_locale_detect": DatapointContract(
        required=False,
        # markdown-only since 2026-09-08 (the hreflang/lang-attribute path
        # was removed - structurally dead against real cleaned markdown).
        null_tolerance_pct=40.0,  # single-language sites often never spell out their language
        source_priority=("markdown",),
    ),
    "pricing_locale_extract": DatapointContract(
        required=False,
        null_tolerance_pct=75.0,  # HIGH - most B2B pages don't publish pricing
        source_priority=("markdown",),
    ),
    "careers_page_parse": DatapointContract(
        required=False,
        null_tolerance_pct=80.0,  # HIGH - most crawled pages aren't a careers page
        source_priority=("markdown",),
    ),
    "tech_stack_normalize": DatapointContract(
        required=False,
        # Lowered from 55.0 on 2026-09-08 after broadening the vendor
        # catalog from 18 to ~75 names across 13 categories - detected_tools
        # context is still frequently unavailable, but mentioned_technologies
        # alone now has meaningfully better recall against real prose.
        null_tolerance_pct=40.0,
        source_priority=("context", "markdown"),
    ),
    "business_model": DatapointContract(
        required=False,
        null_tolerance_pct=35.0,
        source_priority=("context", "markdown"),
        enum_values=(
            ("FREEMIUM", "USAGE", "PERPETUAL", "SUBSCRIPTION"),  # pricing
            ("MARKETPLACE", "HARDWARE", "DATA", "SERVICES", "SAAS"),  # offering
            ("SELF_SERVE", "SALES_LED", "HYBRID"),  # delivery
        ),
    ),
    "company_entity_resolve": DatapointContract(
        required=True,
        null_tolerance_pct=15.0,  # low - this is the canonical join key
        source_priority=("context", "markdown"),
    ),
    "date_normalize": DatapointContract(
        required=False,
        null_tolerance_pct=20.0,  # most pages mention at least one date somewhere
        source_priority=("context", "markdown"),
    ),
    "compliance_framework_extract": DatapointContract(
        required=False,
        null_tolerance_pct=70.0,  # niche - only compliance-forward companies advertise this
        source_priority=("markdown",),
    ),
    "experience_signal_extract": DatapointContract(
        required=False,
        null_tolerance_pct=45.0,
        source_priority=("markdown",),
    ),
    "service_region_extract": DatapointContract(
        required=False,
        null_tolerance_pct=35.0,
        source_priority=("markdown",),
    ),
}


# apify/company/universal/extract.py's extract_company_universal_fields()
# output - one contract per field, all required=False (no join-key-critical
# field lives here; domain_normalize stays Firecrawl's job per
# apify/company/universal/README.md) and all source_priority=("apify",)
# since nothing else produces these fields (yet - see foreman/ for the one
# exception, company_name, which isn't in this dict because it's resolved
# across two sources, not a single-source Apify field).
#
# null_tolerance_pct values below are PROVISIONAL: no live Apify
# integration exists in this repo yet (every apify/*/universal/datapoints/
# module docstring says so), so these are conservative estimates of a
# LinkedIn-company-scrape's typical field-presence rate, not measurements.
# Revisit once a real Apify sample confirms actual hit rate - same
# discipline /review-contract already applies to the Firecrawl contracts
# above.
APIFY_COMPANY_CONTRACTS: Dict[str, DatapointContract] = {
    "name": DatapointContract(
        required=False,
        null_tolerance_pct=15.0,  # a LinkedIn company scrape without a name would be a scrape failure
        source_priority=("apify",),
    ),
    "industry": DatapointContract(
        required=False,
        null_tolerance_pct=35.0,
        source_priority=("apify",),
    ),
    "headcount": DatapointContract(
        required=False,
        null_tolerance_pct=40.0,  # LinkedIn's headcount range is common but not universal
        source_priority=("apify",),
    ),
    "location": DatapointContract(
        required=False,
        null_tolerance_pct=30.0,
        source_priority=("apify",),
    ),
    "linkedin_url": DatapointContract(
        required=False,
        null_tolerance_pct=10.0,  # this is the record's own join key - if Apify returned it, this is almost always present
        source_priority=("apify",),
    ),
}


# apify/people/universal/extract.py's extract_person_universal_fields()
# output. Same provisional-tolerance caveat as APIFY_COMPANY_CONTRACTS
# above - no live Apify integration exists yet.
APIFY_PEOPLE_CONTRACTS: Dict[str, DatapointContract] = {
    "linkedin_url": DatapointContract(
        required=False,
        null_tolerance_pct=10.0,  # the scrape's own join key
        source_priority=("apify",),
    ),
    "full_name": DatapointContract(
        required=False,
        null_tolerance_pct=10.0,  # every LinkedIn profile has a name
        source_priority=("apify",),
    ),
    "job_title": DatapointContract(
        required=False,
        null_tolerance_pct=20.0,
        source_priority=("apify",),
    ),
    "seniority": DatapointContract(
        required=False,
        # added 2026-09-09 (moved from secondary/ - see seniority.py's
        # docstring). Derived from job_title via a keyword ladder that
        # always returns a value once job_title is non-empty (falls back
        # to IC), so its null rate tracks job_title's directly.
        null_tolerance_pct=20.0,
        source_priority=("apify",),
    ),
    "country": DatapointContract(
        required=False,
        null_tolerance_pct=35.0,
        source_priority=("apify",),
    ),
    "linkedin_about": DatapointContract(
        required=False,
        null_tolerance_pct=50.0,  # the About section is frequently left blank
        source_priority=("apify",),
    ),
    "age": DatapointContract(
        required=False,
        # added 2026-09-09. No evidentiary basis at all, unlike the fields
        # above - LinkedIn doesn't publicly expose birthdate/age on a
        # profile, so most Apify actors have nothing to report here. Set
        # high rather than guessed low; see age.py's docstring caveat.
        null_tolerance_pct=95.0,
        source_priority=("apify",),
    ),
    "company_industry": DatapointContract(
        required=False,
        # added 2026-09-09. A flat convenience field some LinkedIn
        # person-actors attach, others don't - no real sample to confirm
        # a rate against yet (see company_industry.py's docstring).
        null_tolerance_pct=50.0,
        source_priority=("apify",),
    ),
}
