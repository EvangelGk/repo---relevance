"""
silver/foreman/priority_rules.py

Per-datapoint priority_rule config for function_source_priority_resolve.

Not a single global source hierarchy -- Apify is not declared "always
wins." Almost every universal field has exactly one live candidate source
today and is tagged statically (`<field>_source`); there's nothing to
resolve there. A rule only needs an entry here once a field genuinely has
2+ live candidate sources -- and each entry picks its OWN ordered list of
criteria, because what makes a source trustworthy differs by datapoint
(a historical fact wants a verified registry; a live headcount number
might instead want "most recently observed").

Today exactly one field qualifies: founded_year (apify, firecrawl,
crunchbase). The shape below scales to any number of sources without
changing -- add a 4th competing source to founded_year, or add a whole
new multi-source field, by editing data here, never the resolver.
"""

from silver.foreman.source_priority_resolve import PriorityRule

PRIORITY_RULES: dict[str, PriorityRule] = {
    "founded_year": {
        # Single criterion is enough here: a fixed reliability ranking.
        #   crunchbase -- investor/registry-diligenced, closest to a legal fact.
        #   firecrawl  -- footer copyright year (legal_entity_extract): a real,
        #                 dated string, but often a rebrand/relaunch year, not
        #                 the true founding year.
        #   apify      -- LinkedIn's self-reported "founded" field: company-
        #                 controlled marketing copy, rarely corrected -- the
        #                 weakest of the three here specifically, even though
        #                 apify is the correct default for almost every other
        #                 company/people datapoint. This is why the priority
        #                 question bites on Apify: everywhere else it wins
        #                 without a contest; here it's the one usually wrong.
        "criteria": [
            {"type": "static_rank", "rank": ["crunchbase", "firecrawl", "apify"]},
        ],
        "normalize": "int",
    },
    # Template for the next multi-source field, not a real entry -- delete
    # once a real one lands. Shows a field that chains two DIFFERENT
    # criteria types instead of one static rank: prefer a source that
    # returned structured data (e.g. schema.org JSON-LD) over free-text
    # scraping, and only fall back to a fixed rank if nothing is structured.
    # "_example_multi_criteria_field": {
    #     "criteria": [
    #         {"type": "prefer_structured", "meta_key": "is_structured"},
    #         {"type": "static_rank", "rank": ["firecrawl", "apify"]},
    #     ],
    #     "normalize": "lower_strip",
    # },
}
