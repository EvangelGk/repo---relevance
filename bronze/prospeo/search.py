"""Runs a ClientContext-driven people search against Prospeo's Search
Person endpoint, scoped to one company at a time - the "search people for
each company in the CSV" half of the automatic pipeline (see
bronze/pipeline.py's run_people_search_for_batch, which calls this once per
already-gated company row from bronze/clay's company search output).

**Company-scoping caveat - UNCONFIRMED, verify live before trusting**:
search_person.py only models `person_job_title` today (see its own
docstring); restricting a search to one specific company isn't grounded
against Prospeo's real filter catalog yet - no live test call has been
made. `_DOMAIN_FILTER_FIELD`/`_NAME_FILTER_FIELD` below are a best-guess at
the raw Prospeo field names, passed through search_person()'s
**extra_filters passthrough. Run one real search (1 credit, against a
company you know is in Prospeo's dataset) before relying on this in
production - if Prospeo rejects the field name outright, this whole
domain-then-name fallback needs redesigning around whatever the real field
turns out to be. The request-body wrapping question flagged in
search_person.py's own review (top-level key vs. a `"filters"` wrapper) is
the same open item and should be resolved by that same live call.

v1 scope (decided in the terminal alongside the ClientContext fields this
reads): job title only, domain match first, falling back to a
company-name match when the domain match returns zero results.
Seniority/department/person-location filters are deliberately not modeled
yet - contracts.py's job-title-only ICP fields are the only signal this
module acts on."""
from typing import Any, Dict, List

from client_context.schema import ClientContext

from .search_person import search_person

# UNCONFIRMED raw Prospeo field names - see module docstring.
_DOMAIN_FILTER_FIELD = "company_website"
_NAME_FILTER_FIELD = "company_name"


def _job_title_kwargs(context: ClientContext) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if context.people_job_title_include:
        kwargs["job_title_include"] = list(context.people_job_title_include)
    if context.people_job_title_exclude:
        kwargs["job_title_exclude"] = list(context.people_job_title_exclude)
    if kwargs:
        kwargs["match_mode"] = context.people_match_mode
    return kwargs


def run_people_search_for_company(
    company_row: Dict[str, Any], context: ClientContext
) -> Dict[str, Any]:
    """Returns {"people": [...], "matched_by": "domain" | "name" | None}.

    `people` is capped client-side at `context.people_max_per_company`
    (no confirmed Prospeo request parameter for this yet - see
    ClientContext.people_max_per_company's docstring).

    Returns an empty result with matched_by=None, without calling Prospeo
    at all, when the ClientContext has no job-title filter configured yet
    - an unscoped global search is never the right call for a per-company
    automatic pipeline - or when the company row has neither a domain nor
    a name to match on."""
    title_kwargs = _job_title_kwargs(context)
    if not title_kwargs:
        return {"people": [], "matched_by": None}

    domain = company_row.get("domain")
    name = company_row.get("name")

    if domain:
        response = search_person(**title_kwargs, **{_DOMAIN_FILTER_FIELD: domain})
        people: List[Dict[str, Any]] = response.get("results") or []
        if people:
            return {"people": people[: context.people_max_per_company], "matched_by": "domain"}

    if name:
        response = search_person(**title_kwargs, **{_NAME_FILTER_FIELD: name})
        people = response.get("results") or []
        if people:
            return {"people": people[: context.people_max_per_company], "matched_by": "name"}

    return {"people": [], "matched_by": None}
