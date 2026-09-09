"""extract_person_universal_fields(raw_apify_person: dict) -> dict

Thin composition, not a datapoint itself: calls each single-field
extractor in `datapoints/` and assembles the flat shape
`silver/people/connector.py` expects (its `apify_person` parameter).

**`seniority` was added here on 2026-09-09** after "universal" was
redefined (at explicit user direction) from "raw-field extractor" to "a
field present on every person record regardless of source shape" - see
`datapoints/seniority.py`'s docstring and `README.md` for the full
rationale. It's still derived (from `job_title`, via a keyword ladder),
not a flat passthrough - that part hasn't changed.

Still deliberately excludes `employed_company` - it needs resolving the
current entry out of the full experience array, a possibly-absent,
multi-record input, not a transform of one always-present scalar the way
`seniority` is. See `apify/people/secondary/datapoints/
experience_array_resolve.py`, which `silver/people/connector.py` calls
directly for this instead of trusting a flat passthrough field Apify
never actually returns.
"""
from typing import Any, Dict, Optional

from .datapoints.age import extract_age
from .datapoints.company_industry import extract_company_industry
from .datapoints.country import extract_country
from .datapoints.full_name import extract_full_name
from .datapoints.job_title import extract_job_title
from .datapoints.linkedin_about import extract_linkedin_about
from .datapoints.linkedin_url import extract_linkedin_url
from .datapoints.seniority import function_seniority


def extract_person_universal_fields(raw_apify_person: Optional[Dict[str, Any]]) -> Dict[str, Optional[Any]]:
    raw = raw_apify_person or {}
    job_title = extract_job_title(raw)
    return {
        "linkedin_url": extract_linkedin_url(raw),
        "full_name": extract_full_name(raw),
        "job_title": job_title,
        "seniority": function_seniority(job_title),
        "country": extract_country(raw),
        "linkedin_about": extract_linkedin_about(raw),
        "age": extract_age(raw),
        "company_industry": extract_company_industry(raw),
    }
