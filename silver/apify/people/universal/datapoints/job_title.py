"""extract_job_title(raw_apify_person: dict) -> str | None

Raw free-text job title off the Apify LinkedIn person record. Feeds
`apify/people/secondary/datapoints/seniority.py`.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_job_title(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_person or {}
    return first(raw, "job_title", "jobTitle", "headline", "occupation")
