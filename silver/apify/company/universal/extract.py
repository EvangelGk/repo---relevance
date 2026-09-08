"""extract_company_universal_fields(raw_apify_company: dict) -> dict

Thin composition, not a datapoint itself: calls each single-field
extractor in `datapoints/` and assembles the flat shape
`silver/company/connector.py` expects (its `apify_company` parameter) -
the same relationship `Firecrawl.run_all()` has to `firecrawl/datapoints/`,
just without a registry/order dependency since none of these fields read
each other's output.
"""
from typing import Any, Dict, Optional

from .datapoints.headcount import extract_headcount
from .datapoints.industry import extract_industry
from .datapoints.linkedin_url import extract_linkedin_url
from .datapoints.location import extract_location
from .datapoints.name import extract_name


def extract_company_universal_fields(raw_apify_company: Optional[Dict[str, Any]]) -> Dict[str, Optional[Any]]:
    raw = raw_apify_company or {}
    return {
        "name": extract_name(raw),
        "industry": extract_industry(raw),
        "headcount": extract_headcount(raw),
        "location": extract_location(raw),
        "linkedin_url": extract_linkedin_url(raw),
    }
