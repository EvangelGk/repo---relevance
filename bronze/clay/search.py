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

This module returns Clay's raw PublicApiCompanySearchResult dicts,
unmodified. Merging them onto a Silver row (keyed by domain_normalize,
which is exactly the "domain" field these results carry) is a separate
step and not this function's job - see the CLAUDE.md discussion of the
clean/dedupe vs. enrich-waterfall split this repo is built around.
"""
from typing import Any, Dict, List

from client_context.schema import ClientContext

from . import _http
from .query_builder import build_company_query

# Per Clay's confirmed openapi schema for POST /search/query-mode/{id}/run:
# `limit` defaults to 20, max 500 per call.
_MAX_PAGE_SIZE = 500


def run_company_search(context: ClientContext) -> Dict[str, Any]:
    """Returns {"companies": [...], "source_type": str, "query": str}.

    `query` is included so a caller (or a human debugging a confusing
    zero-result run) can see exactly what was sent to Clay without having
    to re-derive it from the ClientContext."""
    query = build_company_query(context)
    created = _http.post("/search/query-mode", {"query": query})
    search_id = created["search_id"]
    source_type = created.get("source_type")

    companies: List[Dict[str, Any]] = []
    remaining = context.limit
    while remaining > 0:
        page_size = min(remaining, _MAX_PAGE_SIZE)
        result = _http.post(f"/search/query-mode/{search_id}/run", {"limit": page_size})
        page = result.get("data", [])
        companies.extend(page)
        remaining -= len(page)
        if not result.get("has_more") or not page:
            break

    return {"companies": companies, "source_type": source_type, "query": query}
