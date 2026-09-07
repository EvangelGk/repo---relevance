"""Validates the "row" half of Firecrawl.run_all() against
contracts.DATAPOINT_CONTRACTS.

pandera's Column-based DataFrameSchema fits flat/scalar checks cleanly - is
domain_normalize a plausible domain string, is company_entity_resolve's
company_id non-empty, are business_model's/regulatory_event_classify's enum
sub-fields in their allowed set - but it doesn't fit the nested dict/list
fields Firecrawl actually returns (social_links_extract is a dict of six
optional URLs, careers_page_parse is a list of role dicts): a pandera Column
check would just receive the whole dict/list as one cell and have to
re-implement Python shape-checking inside a lambda anyway, so those two are
validated directly with plain Python type/shape checks instead of forcing
them through pandera for no real benefit.

_check_no_placeholder_strings (added 2026-09-07, adapted from a B2B
account-research crawl-extraction prompt's "never emit N/A/Unknown/null"
rule) is a third kind of plain-Python check: it doesn't validate a
function's *shape*, it validates that "nothing found" was reported as
None/[]/{} - the convention every extractor already follows via
Firecrawl._collapse_if_blank - rather than as a literal placeholder string,
which would read as a real (wrong) answer to anything downstream.
"""
import re
from typing import Any, List, Optional

import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

from .contracts import DATAPOINT_CONTRACTS

_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")

_SOCIAL_LINK_KEYS = {
    "linkedin_url", "twitter_url", "crunchbase_url", "g2_url", "capterra_url", "youtube_url",
}
_CAREER_ROLE_KEYS = {"title", "department", "location", "posted_date"}

# Compared against a stripped, lowercased whole-value string - not a
# substring search, so a legitimate value that merely contains one of
# these words ("Not Applicable Services LLC") is never falsely flagged.
_PLACEHOLDER_STRING_TOKENS = {
    "n/a", "na", "unknown", "none", "null", "not specified", "not available", "tbd",
}


def _is_plausible_domain(value: Any) -> bool:
    return value is None or (isinstance(value, str) and bool(_DOMAIN_RE.match(value)))


def _has_company_id(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.get("company_id"))


def _business_model_enums_ok(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, dict):
        return False
    pricing_enum, offering_enum, delivery_enum = DATAPOINT_CONTRACTS["business_model"].enum_values
    for sub_field, allowed in (("pricing", pricing_enum), ("offering", offering_enum), ("delivery", delivery_enum)):
        primary = (value.get(sub_field) or {}).get("primary")
        if primary is not None and primary not in allowed:
            return False
    return True


def _regulatory_enum_ok(value: Any) -> bool:
    if value is None:
        return True
    allowed = DATAPOINT_CONTRACTS["regulatory_event_classify"].enum_values
    return value in allowed


# No dtype is declared on any Column below (on purpose): the row dict's
# values can be plain Python str, dict, or None in the same column across
# different pages, and pandas 3's default string dtype inference (a bare
# "str" dtype rather than the legacy "object") would otherwise make
# pandera's dtype check fail on values these Checks are perfectly able to
# validate directly - the Check callables are what matters here, not the
# backing dtype.
_ROW_SCHEMA = DataFrameSchema(
    {
        "domain_normalize": Column(checks=Check(lambda s: s.map(_is_plausible_domain)), nullable=True, required=False),
        "company_entity_resolve": Column(
            checks=Check(lambda s: s.map(lambda v: v is None or _has_company_id(v))),
            nullable=True,
            required=False,
        ),
        "business_model": Column(
            checks=Check(lambda s: s.map(_business_model_enums_ok)), nullable=True, required=False
        ),
        "regulatory_event_classify": Column(
            checks=Check(lambda s: s.map(_regulatory_enum_ok)), nullable=True, required=False
        ),
    },
    strict=False,
    coerce=False,
)


def _check_social_links_shape(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return ["social_links_extract: expected a dict, got " + type(value).__name__]
    violations = []
    unknown_keys = set(value) - _SOCIAL_LINK_KEYS
    if unknown_keys:
        violations.append(f"social_links_extract: unexpected keys {sorted(unknown_keys)}")
    for key, url in value.items():
        if url is not None and not isinstance(url, str):
            violations.append(f"social_links_extract.{key}: expected str or None, got {type(url).__name__}")
    return violations


def _check_careers_shape(value: Any) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return ["careers_page_parse: expected a list, got " + type(value).__name__]
    violations = []
    for i, role in enumerate(value):
        if not isinstance(role, dict):
            violations.append(f"careers_page_parse[{i}]: expected a dict, got {type(role).__name__}")
            continue
        missing_keys = _CAREER_ROLE_KEYS - set(role)
        if missing_keys:
            violations.append(f"careers_page_parse[{i}]: missing keys {sorted(missing_keys)}")
    return violations


def _contains_placeholder_string(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in _PLACEHOLDER_STRING_TOKENS
    if isinstance(value, dict):
        return any(_contains_placeholder_string(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_placeholder_string(v) for v in value)
    return False


def _check_no_placeholder_strings(row: dict) -> List[str]:
    """An extractor should report "nothing found" as None/[]/{} (the
    Firecrawl._collapse_if_blank convention every one of the 17 datapoint
    functions already follows) - never as a literal placeholder string.
    Scoped to the 17 contracted datapoint fields only, so metadata columns
    like raw_markdown_input/run_timestamp/crawl_issue can't false-positive
    (crawl_issue's own value is legitimately the word "none")."""
    violations = []
    for name in DATAPOINT_CONTRACTS:
        if _contains_placeholder_string(row.get(name)):
            violations.append(f"{name}: contains a placeholder string instead of empty (None/[]/{{}})")
    return violations


def evaluate_row(row: dict) -> List[str]:
    """Validate one Firecrawl "row" dict against DATAPOINT_CONTRACTS.
    Returns a list of violation strings - empty means the row passes every
    hard requirement."""
    violations: List[str] = []

    # Hard requirements: required=True contracts must have a value, checked
    # at the specific sub-field the rest of the pipeline actually joins on.
    if DATAPOINT_CONTRACTS["domain_normalize"].required and not row.get("domain_normalize"):
        violations.append("domain_normalize: required but missing")
    if DATAPOINT_CONTRACTS["company_entity_resolve"].required and not _has_company_id(
        row.get("company_entity_resolve")
    ):
        violations.append("company_entity_resolve.company_id: required but missing")

    # Scalar/enum shape checks via pandera.
    df = pd.DataFrame([row])
    try:
        _ROW_SCHEMA.validate(df, lazy=True)
    except pa.errors.SchemaErrors as exc:
        for _, failure in exc.failure_cases.iterrows():
            violations.append(f"{failure['column']}: failed check {failure['check']} (value={failure['failure_case']!r})")

    # Nested dict/list shape checks - plain Python, not pandera (see module docstring).
    violations.extend(_check_social_links_shape(row.get("social_links_extract")))
    violations.extend(_check_careers_shape(row.get("careers_page_parse")))
    violations.extend(_check_no_placeholder_strings(row))

    return violations
