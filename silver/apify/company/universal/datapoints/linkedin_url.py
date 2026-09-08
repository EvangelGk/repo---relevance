"""extract_linkedin_url(raw_apify_company: dict) -> str | None

The company's own LinkedIn page URL, straight off the raw Apify record -
distinct from `domain_normalize` (Firecrawl-side, the website root
domain).
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_linkedin_url(raw_apify_company: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_company or {}
    return first(raw, "linkedin_url", "linkedinUrl", "url", "companyUrl")
