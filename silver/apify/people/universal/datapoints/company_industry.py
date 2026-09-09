"""extract_company_industry(raw_apify_person: dict) -> str | None

The industry of the person's *current employer*, as a flat convenience
field off the raw Apify LinkedIn person record - not derived by joining
against `apify/company/universal/datapoints/industry.py`'s output. Some
LinkedIn person-actor scrapes attach the current company's industry
directly on the profile record; when they don't, this returns `None`
rather than attempting a company-record join (no such join is wired
anywhere in this repo yet - see `silver/people/connector.py`'s
`employed_company` docstring for the equivalent, still-open gap on the
company-name side).
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_company_industry(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_person or {}
    return first(raw, "company_industry", "companyIndustry", "currentCompanyIndustry")
