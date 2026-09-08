"""extract_person_universal_fields(raw_apify_person: dict) -> dict

Thin composition, not a datapoint itself: calls each single-field
extractor in `datapoints/` and assembles the flat shape
`silver/people/connector.py` expects (its `apify_person` parameter).

Deliberately excludes `seniority` and `employed_company` - despite being
listed as "universal" fields in the original plan, neither is actually a
raw Apify field:
  - `seniority` needs derivation from job title -
    see `apify/people/secondary/datapoints/seniority.py`.
  - `employed_company` needs resolving the current entry out of the full
    experience array - see `apify/people/secondary/datapoints/
    experience_array_resolve.py`, which `silver/people/connector.py` calls
    directly for this instead of trusting a flat passthrough field Apify
    never actually returns.
"""
from typing import Any, Dict, Optional

from .datapoints.country import extract_country
from .datapoints.full_name import extract_full_name
from .datapoints.job_title import extract_job_title
from .datapoints.linkedin_about import extract_linkedin_about
from .datapoints.linkedin_url import extract_linkedin_url


def extract_person_universal_fields(raw_apify_person: Optional[Dict[str, Any]]) -> Dict[str, Optional[Any]]:
    raw = raw_apify_person or {}
    return {
        "linkedin_url": extract_linkedin_url(raw),
        "full_name": extract_full_name(raw),
        "job_title": extract_job_title(raw),
        "country": extract_country(raw),
        "linkedin_about": extract_linkedin_about(raw),
    }
