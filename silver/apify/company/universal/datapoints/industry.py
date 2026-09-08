"""extract_industry(raw_apify_company: dict) -> str | None

Company industry label, straight off the raw Apify LinkedIn company
record. Firecrawl's `business_model`/`tech_stack_normalize` corroborate
this but never override it - this stays the authoritative value.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_industry(raw_apify_company: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_company or {}
    return first(raw, "industry", "companyIndustry")
