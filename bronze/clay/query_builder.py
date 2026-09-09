"""Translates a ClientContext (client_context/schema.py) into a Clay
search-query-language string for POST /search/query-mode.

Grounded against the `clay-search-query` skill reference (the fuller,
worked-example-backed authoring guide Clay itself publishes for this DSL -
see repo -- relevance -- context/clay-search-query/clay-search-query/SKILL.md
on this machine), which supersedes the narrower live
GET /search/query-mode/reference pull this module was originally grounded
in on 2026-09-08. Every clause below cites the specific skill section it
follows. Nothing here invents Clay syntax; where the skill doesn't confirm
a case, that field is simply left out of the query rather than guessed at.

Deliberately NOT handled here: the query-string `limit` clause the DSL
grammar allows (`limit_by? limit?`) - its interaction with the separate
per-run `limit` parameter on POST /search/query-mode/{id}/run isn't
confirmed by the reference doc, so search.py paginates using only the
run-endpoint's own `limit`, driven by ClientContext.limit, rather than
embedding a second, possibly-conflicting limit inside the query text.
"""
from typing import List, Optional, Sequence

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
    # subfields. "OR alternatives (any one of) can share one
    # .any(... in (...))" (Company keyword matching section) - one scan
    # covering every requested tech, not one .any() per tech OR'd
    # together (each .any() is its own scan - see the Experience
    # expressions section's cost note, which applies to tuple-array scans
    # generally, not just experiences.any()).
    if context.technologies:
        techs = _quoted_list(context.technologies)
        clauses.append(f"technographics.any(vendor in {techs} or product in {techs})")

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


def build_people_query(context: ClientContext) -> Optional[str]:
    """Returns a `select from people where experiences.any(...)` query
    string, or None when the context has no positive job-title filter.

    Mirrors bronze/prospeo/search.py's own "an unscoped global search is
    never the right call" guard: without a job_title criterion this would
    be "everyone currently employed anywhere", which is never a useful
    Clay call, so - like run_people_search_for_company - this returns None
    rather than a query that would need to be run and then discarded.

    Every condition below lives inside ONE experiences.any(...) block, per
    the skill's "Experience expressions" section: splitting one role's
    conditions across multiple experiences.any() calls changes the
    meaning (each arm could then be satisfied by a *different* experience)
    and costs one extra table scan per arm. `is_current = true` is the
    default per the "Role and tenure defaults" table - this repo's
    ClientContext has no "former employee" concept to opt out of it with.
    """
    if not context.people_job_title_include:
        return None

    # "Default to is_similar_to for job_title" (Operators section) - best
    # recall; ClientContext's include/exclude lists are role keywords, not
    # literal-match requests.
    inner: List[str] = ["is_current = true"]
    inner.append(f"job_title is_similar_to {_quoted_list(context.people_job_title_include)}")

    # "Never drop negation/exclusion clauses ... not job_title is_similar_to
    # (X)" (Common query guardrails section) - kept as its own predicate
    # inside the same experiences.any(), not a separate arm.
    if context.people_job_title_exclude:
        inner.append(f"not job_title is_similar_to {_quoted_list(context.people_job_title_exclude)}")

    # Employer-side ICP scoping, all inside the same experiences.any() per
    # the "one arm per role" rule - reads this ClientContext's own company
    # criteria as the target employer's profile, via the company.* scalar/
    # tuple-array fields the Experience expressions section documents as
    # valid inside an experience expression.
    if context.industries:
        inner.append(f"company.industry in {_quoted_list(context.industries)}")
    if context.company_size_buckets:
        inner.append(f"company.company_size in {_quoted_list(context.company_size_buckets)}")
    if context.hq_countries or context.hq_cities:
        loc_inner = ["is_headquarters = true"]
        if context.hq_countries:
            loc_inner.append(f"country_name in {_quoted_list(context.hq_countries)}")
        if context.hq_cities:
            loc_inner.append(f"city in {_quoted_list(context.hq_cities)}")
        inner.append("company.locations.any(" + " and ".join(loc_inner) + ")")
    if context.technologies:
        techs = _quoted_list(context.technologies)
        inner.append(f"company.technographics.any(vendor in {techs} or product in {techs})")
    if context.products_and_services:
        inner.append(
            f"company.products_and_services is_similar_to {_quoted_list(context.products_and_services)}"
        )
    if context.description_keywords:
        inner.append(f"company.description contains {_quoted_list(context.description_keywords)}")

    where_clause = "\nwhere\n  experiences.any(" + " and ".join(inner) + ")"
    return f"select from people{where_clause}"


def build_people_query_for_domains(
    domains: Sequence[str],
    job_title_include: Sequence[str],
    job_title_exclude: Sequence[str] = (),
) -> Optional[str]:
    """Returns a `select from people where clay.filter_to_companies(...)
    and experiences.any(...)` query, or None when `domains` or
    `job_title_include` is empty.

    Unlike build_people_query() (which scopes the target employer via
    company.industry/company_size/locations *inside* experiences.any() -
    an ICP proxy), this scopes to an exact, already-resolved company list -
    e.g. the output of a prior run_company_search() - via
    clay.filter_to_companies(...) at the top level. Per the skill's
    "Company Identification" section: "For current employer matching from
    explicit company domains ... use clay.filter_to_companies(...) at the
    top level. This matches people currently at the identified companies.
    Do NOT wrap it in experiences.any(...)." Combined with a role filter
    per its own worked example: `clay.filter_to_companies((...)) and
    experiences.any(is_current = true and job_title is_similar_to (...))`
    - so no company.* fields belong inside this experiences.any() block,
    since clay.filter_to_companies already pins the exact employer.
    """
    if not domains or not job_title_include:
        return None

    inner: List[str] = ["is_current = true"]
    inner.append(f"job_title is_similar_to {_quoted_list(job_title_include)}")
    if job_title_exclude:
        inner.append(f"not job_title is_similar_to {_quoted_list(job_title_exclude)}")

    return (
        "select from people\n"
        "where\n"
        f"  clay.filter_to_companies({_quoted_list(domains)})\n"
        f"  and experiences.any({' and '.join(inner)})"
    )
