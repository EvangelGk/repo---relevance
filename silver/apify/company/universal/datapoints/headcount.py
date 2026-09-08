"""extract_headcount(raw_apify_company: dict) -> int | None

Raw employee-count figure off the Apify LinkedIn company record. Feeds
`apify/company/secondary/datapoints/headcount_band.py`.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_headcount(raw_apify_company: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_company or {}
    return first(raw, "headcount", "employeeCount", "staffCount", "companySize")
