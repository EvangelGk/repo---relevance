"""Runs a ClientContext-driven company search against Clay's public API -
Artemis step 3 ("pull from source"), the Clay half of it (see
ARTEMIS_CONTEXT.md's step split and the terminal conversation that scoped
this: Clay for its own brokered search, terminal/Apify/SerpAPI for
everything else).

Two-step Clay flow, per GET /search/query-mode/reference and the
confirmed openapi paths (fetched/verified 2026-09-08):
  1. POST /search/query-mode {"query": "..."} -> {"search_id", "source_type"}
  2. POST /search/query-mode/{search_id}/run {"limit": N} -> {"data", "has_more", ...}
   , called repeatedly (paging on has_more) until ClientContext.limit results
  are collected or Clay reports no more results.

This module returns Clay's raw PublicApiCompanySearchResult /
PublicApiPeopleSearchResult dicts, unmodified. Merging them onto a Silver
row (keyed by domain_normalize, which is exactly the "domain" field these
results carry) is a separate step and not this function's job - see the
CLAUDE.md discussion of the clean/dedupe vs. enrich-waterfall split this
repo is built around.

**Added 2026-09-09**: run_people_search() runs the identical two-step flow
against a `select from people` query (build_people_query()) instead of
`select from companies` - the same POST /search/query-mode endpoint, the
same search_id/has_more pagination contract, just a different query
string. Both entry points share `_run_query_mode_search()` below rather
than duplicating the pagination loop.
"""
from typing import Any, Dict, List, Sequence

from client_context.schema import ClientContext

from . import _http
from .query_builder import build_company_query, build_people_query, build_people_query_for_domains

# Per Clay's confirmed openapi schema for POST /search/query-mode/{id}/run:
# `limit` defaults to 20, max 500 per call.
_MAX_PAGE_SIZE = 500


def _run_query_mode_search(query: str, limit: int) -> Dict[str, Any]:
    """Returns {"results": [...], "source_type": str}. Shared by
    run_company_search/run_people_search - identical create+paginate flow
    for both entities, per POST /search/query-mode's shared contract."""
    created = _http.post("/search/query-mode", {"query": query})
    search_id = created["search_id"]
    source_type = created.get("source_type")

    results: List[Dict[str, Any]] = []
    remaining = limit
    while remaining > 0:
        page_size = min(remaining, _MAX_PAGE_SIZE)
        page_result = _http.post(f"/search/query-mode/{search_id}/run", {"limit": page_size})
        page = page_result.get("data", [])
        results.extend(page)
        remaining -= len(page)
        if not page_result.get("has_more") or not page:
            break

    return {"results": results, "source_type": source_type}


def run_company_search(context: ClientContext) -> Dict[str, Any]:
    """Returns {"companies": [...], "source_type": str, "query": str}.

    `query` is included so a caller (or a human debugging a confusing
    zero-result run) can see exactly what was sent to Clay without having
    to re-derive it from the ClientContext."""
    query = build_company_query(context)
    run = _run_query_mode_search(query, context.limit)
    return {"companies": run["results"], "source_type": run["source_type"], "query": query}


def run_people_search(context: ClientContext) -> Dict[str, Any]:
    """Returns {"people": [...], "source_type": str | None, "query": str | None}.

    Returns an empty result without calling Clay at all when
    build_people_query() returns None (no job-title filter configured) -
    mirrors bronze/prospeo/search.py's run_people_search_for_company's own
    "an unscoped global search is never the right call" guard."""
    query = build_people_query(context)
    if query is None:
        return {"people": [], "source_type": None, "query": None}

    run = _run_query_mode_search(query, context.limit)
    return {"people": run["results"], "source_type": run["source_type"], "query": query}


def run_people_search_for_domains(
    domains: Sequence[str],
    job_title_include: Sequence[str],
    job_title_exclude: Sequence[str] = (),
    limit: int = 100,
) -> Dict[str, Any]:
    """Same shape as run_people_search(), but scoped to an exact,
    already-resolved company list (e.g. domains from a prior
    run_company_search()) via build_people_query_for_domains() instead of
    the industry/size/location ICP-proxy build_people_query() uses. Use
    this once you already have real companies and want the people at
    exactly those companies, not a fresh ICP-driven company guess."""
    query = build_people_query_for_domains(domains, job_title_include, job_title_exclude)
    if query is None:
        return {"people": [], "source_type": None, "query": None}

    run = _run_query_mode_search(query, limit)
    return {"people": run["results"], "source_type": run["source_type"], "query": query}
