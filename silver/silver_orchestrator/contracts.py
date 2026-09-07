"""Single source of truth for what each of Firecrawl's 17 datapoint
functions is contractually expected to produce - mirrors the finance
project's SeriesContract/SourceContract pattern: frozen dataclasses instead
of magic numbers scattered across schema_gate.py, quality_score.py, and
drift.py.

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
        null_tolerance_pct=10.0,  # almost every page resolves to some root domain
        source_priority=("context", "markdown"),
    ),
    "structured_data_extract": DatapointContract(
        required=False,
        null_tolerance_pct=60.0,  # most pages have no JSON-LD Organization block
        source_priority=("html",),
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
        null_tolerance_pct=40.0,  # single-language sites often carry no lang/hreflang tag at all
        source_priority=("hreflang", "markdown_fallback"),
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
        null_tolerance_pct=55.0,  # detected_tools context is frequently unavailable
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
    "regulatory_event_classify": DatapointContract(
        required=False,
        null_tolerance_pct=90.0,  # HIGH - most companies never appear in a regulatory event
        source_priority=("context", "markdown"),
        enum_values=("RECALL", "APPROVAL", "WARNING_LETTER", "LICENSE_GRANTED", "LICENSE_REVOKED", "OTHER"),
    ),
    "date_normalize": DatapointContract(
        required=False,
        null_tolerance_pct=20.0,  # most pages mention at least one date somewhere
        source_priority=("context", "markdown"),
    ),
    "timeseries_snapshot": DatapointContract(
        required=False,
        null_tolerance_pct=55.0,  # needs an explicit value or structured_data's employee count
        source_priority=("context",),
    ),
    "freshness": DatapointContract(
        required=False,
        null_tolerance_pct=70.0,  # needs last_enriched_date, absent on a page's first-ever run
        source_priority=("context",),
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
