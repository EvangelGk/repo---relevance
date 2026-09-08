"""Translates a ClientContext (client_context/schema.py) into a Clay
search-query-language string for POST /search/query-mode.

Every clause below implements a specific rule from Clay's own query-mode
DSL reference (GET /search/query-mode/reference, fetched 2026-09-08) - see
the comment above each clause for which rule it follows. Nothing here
invents Clay syntax; where the reference doc doesn't confirm a case (e.g.
there's no confirmed negative/exclude form for technographics or
description keywords), that field is simply left out of the query rather
than guessed at.

Deliberately NOT handled here: the query-string `limit` clause the DSL
grammar allows (`limit_by? limit?`) - its interaction with the separate
per-run `limit` parameter on POST /search/query-mode/{id}/run isn't
confirmed by the reference doc, so search.py paginates using only the
run-endpoint's own `limit`, driven by ClientContext.limit, rather than
embedding a second, possibly-conflicting limit inside the query text.
"""
from typing import List

from client_context.schema import ClientContext


def _quoted_list(values) -> str:
    return "(" + ", ".join(f'"{v}"' for v in values) + ")"


def build_company_query(context: ClientContext) -> str:
    """Returns a `select from companies where ...` query string, or a
    bare `select from companies` when the context has no filters at all
    (an empty ClientContext is a valid, if unhelpful, query)."""
    clauses: List[str] = []

    # "Default to `industry` for company vertical filtering" - Companies query guardrails.
    if context.industries:
        clauses.append(f"industry in {_quoted_list(context.industries)}")

    # "Use buckets first" for company size - Company size and revenue section.
    if context.company_size_buckets:
        clauses.append(f"company_size in {_quoted_list(context.company_size_buckets)}")

    # Generic HQ location ask -> locations.any(is_headquarters = true and ...)
    # - Location filtering section's "Companies" subsection. Both
    # hq_countries and hq_cities land inside the SAME locations.any(...)
    # predicate (not two separate ones) per that section's worked examples.
    if context.hq_countries or context.hq_cities:
        inner = ["is_headquarters = true"]
        if context.hq_countries:
            inner.append(f"country_name in {_quoted_list(context.hq_countries)}")
        if context.hq_cities:
            inner.append(f"city in {_quoted_list(context.hq_cities)}")
        clauses.append("locations.any(" + " and ".join(inner) + ")")

    # technographics is a tuple array of {vendor, product, product_category}
    # (Array expressions / Companies fields sections) - a client's
    # "uses Salesforce" style ask rarely distinguishes vendor name from
    # product name, so each requested tech is checked against both
    # subfields inside its own .any(...), OR'd together.
    if context.technologies:
        per_tech = " or ".join(
            f'technographics.any(vendor = "{tech}" or product = "{tech}")'
            for tech in context.technologies
        )
        clauses.append(f"({per_tech})" if len(context.technologies) > 1 else per_tech)

    # "products_and_services... Only supports is_similar_to" - Companies fields.
    if context.products_and_services:
        clauses.append(
            f"products_and_services is_similar_to {_quoted_list(context.products_and_services)}"
        )

    # description contains (...) - reserved for self-describing product/
    # service keywords per the Companies query guardrails' worked SaaS
    # example ("a company never self-describes as SaaS..."), never for
    # vertical labels - those go through `industries` above.
    if context.description_keywords:
        clauses.append(f"description contains {_quoted_list(context.description_keywords)}")

    # "For explicit company exclusion lists, use exactly one inline
    # clay.exclude_company_identifiers((...)) call" - Companies query guardrails.
    #
    # CONFIRMED LIVE 2026-09-08: every domain in this list must resolve to
    # a real company Clay knows about, or the *entire* /run call fails with
    # HTTP 400 ("No matching companies found for the provided
    # identifiers.") - not a partial result with the bad entry skipped. A
    # real client's exclude_domains (e.g. "already a customer") list will
    # eventually contain one stale/acquired/typo'd domain; that one entry
    # currently takes the whole search down. No known-good handling exists
    # yet - a caller passing exclude_domains should be ready to catch
    # ClayAPIError and either drop the offending domain and retry, or
    # verify every domain resolves before searching.
    if context.exclude_domains:
        clauses.append(f"clay.exclude_company_identifiers({_quoted_list(context.exclude_domains)})")

    if not clauses:
        return "select from companies"
    where_clause = "\nwhere\n  " + "\n  and ".join(clauses)
    return f"select from companies{where_clause}"
