"""Prospeo's Search Person endpoint - a real discovery/sourcing dataset
(200M+ contacts, 30+ filters per prospeo.io/api-docs), not an enrichment
call. This is the "primary source for people" half of the terminal
discussion: cheap and broad (1 credit per successful search, up to 25
results per credit, free on a repeated query within 30 days per Prospeo's
own dedup), and - critically - it does NOT reveal email/mobile. Those
fields are present on each result but always null/masked; only
enrich_person.py's separate call reveals them, at a separate, higher cost
(1 credit/email, 10 credits/mobile).

That split is deliberate on Prospeo's side and this module preserves it on
purpose: gate on what search_person() already gives you (title, seniority,
company, location) BEFORE calling enrich_person() - the same "gate before
you spend" discipline the rest of this repo already runs (triage.py before
Firecrawl, is_valid_row before a Clay enrichment call). Calling
enrich_person() for every search result indiscriminately is exactly what
this module is meant to help you avoid.

PLACEHOLDER: only the job-title filter is modeled explicitly here, since
that's the one grounded in this conversation. Prospeo's other ~30 filters
(company, seniority, location, etc.) can be passed through **extra_filters
by their raw Prospeo field name until each is confirmed and given its own
named parameter.

Note: Prospeo's filtering is include/exclude lists + a match_mode
("CONTAINS" etc.), not literal boolean AND/OR/NOT operator syntax.
"""
from typing import Any, Dict, List, Optional

from . import _http


def search_person(
    job_title_include: Optional[List[str]] = None,
    job_title_exclude: Optional[List[str]] = None,
    match_mode: str = "CONTAINS",
    page: int = 1,
    **extra_filters: Any,
) -> Dict[str, Any]:
    """Returns Prospeo's raw Search Person response: a page of person +
    company objects (email/mobile present but unrevealed), pagination
    metadata, and credit info. `page` is 1-indexed; each page holds up to
    25 results (Prospeo's own per-page/per-credit cap)."""
    body: Dict[str, Any] = {"page": page}

    if job_title_include or job_title_exclude:
        title_filter: Dict[str, Any] = {"match_mode": match_mode}
        if job_title_include:
            title_filter["include"] = list(job_title_include)
        if job_title_exclude:
            title_filter["exclude"] = list(job_title_exclude)
        body["person_job_title"] = title_filter

    body.update(extra_filters)
    return _http.post("/search-person", body)
