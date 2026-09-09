"""Tests for bronze.clay.query_builder - pure string-building, no network.
Each test pins one ClientContext field to one exact DSL clause, cross-
referenced against Clay's live query-mode/reference doc (fetched
2026-09-08) rather than an assumed shape."""
from client_context.schema import ClientContext
from bronze.clay.query_builder import (
    build_company_query,
    build_people_query,
    build_people_query_for_domains,
)


def _context(**overrides) -> ClientContext:
    defaults = {"client_id": "test", "name": "Test"}
    defaults.update(overrides)
    return ClientContext(**defaults)


def test_empty_context_is_a_bare_select():
    assert build_company_query(_context()) == "select from companies"


def test_industries_use_in_list():
    query = build_company_query(_context(industries=("Software Development",)))
    assert 'industry in ("Software Development")' in query


def test_company_size_buckets_use_in_list():
    query = build_company_query(_context(company_size_buckets=("51-200", "201-500")))
    assert 'company_size in ("51-200", "201-500")' in query


def test_hq_country_and_city_share_one_locations_any_predicate():
    query = build_company_query(
        _context(hq_countries=("United States",), hq_cities=("San Francisco",))
    )
    assert (
        'locations.any(is_headquarters = true and country_name in ("United States") '
        'and city in ("San Francisco"))' in query
    )


def test_hq_country_only_still_sets_is_headquarters_true():
    query = build_company_query(_context(hq_countries=("Germany",)))
    assert 'locations.any(is_headquarters = true and country_name in ("Germany"))' in query


def test_technologies_check_both_vendor_and_product_subfields_in_one_scan():
    query = build_company_query(_context(technologies=("Salesforce", "HubSpot")))
    assert (
        'technographics.any(vendor in ("Salesforce", "HubSpot") '
        'or product in ("Salesforce", "HubSpot"))' in query
    )


def test_products_and_services_uses_is_similar_to():
    query = build_company_query(_context(products_and_services=("b2b saas", "crm")))
    assert 'products_and_services is_similar_to ("b2b saas", "crm")' in query


def test_description_keywords_use_contains():
    query = build_company_query(_context(description_keywords=("card issuing",)))
    assert 'description contains ("card issuing")' in query


def test_exclude_domains_use_clay_exclude_company_identifiers():
    query = build_company_query(_context(exclude_domains=("acme.com", "beta.com")))
    assert 'clay.exclude_company_identifiers(("acme.com", "beta.com"))' in query


def test_multiple_filters_are_and_joined():
    query = build_company_query(
        _context(industries=("Banking",), company_size_buckets=("51-200",))
    )
    assert query == (
        "select from companies\n"
        "where\n"
        '  industry in ("Banking")\n'
        '  and company_size in ("51-200")'
    )


def test_people_query_is_none_without_a_job_title_filter():
    assert build_people_query(_context()) is None
    assert build_people_query(_context(industries=("Banking",))) is None


def test_people_query_uses_is_similar_to_inside_one_experiences_any():
    query = build_people_query(_context(people_job_title_include=("VP Sales", "CRO")))
    assert query == (
        "select from people\n"
        "where\n"
        "  experiences.any(is_current = true "
        'and job_title is_similar_to ("VP Sales", "CRO"))'
    )


def test_people_query_keeps_the_exclusion_inside_the_same_experiences_any():
    query = build_people_query(
        _context(
            people_job_title_include=("engineer",),
            people_job_title_exclude=("intern",),
        )
    )
    assert query == (
        "select from people\n"
        "where\n"
        "  experiences.any(is_current = true "
        'and job_title is_similar_to ("engineer") '
        'and not job_title is_similar_to ("intern"))'
    )


def test_people_query_scopes_to_the_target_employer_profile():
    query = build_people_query(
        _context(
            people_job_title_include=("VP Sales",),
            industries=("Financial Services",),
            company_size_buckets=("51-200",),
            hq_countries=("United States",),
        )
    )
    assert query == (
        "select from people\n"
        "where\n"
        "  experiences.any(is_current = true "
        'and job_title is_similar_to ("VP Sales") '
        'and company.industry in ("Financial Services") '
        'and company.company_size in ("51-200") '
        'and company.locations.any(is_headquarters = true '
        'and country_name in ("United States")))'
    )


def test_domain_query_is_none_without_domains_or_titles():
    assert build_people_query_for_domains([], ["VP Sales"]) is None
    assert build_people_query_for_domains(["acme.com"], []) is None


def test_domain_query_uses_filter_to_companies_outside_experiences_any():
    query = build_people_query_for_domains(
        ["stripe.com", "openai.com"], ["Chief Medical Officer"]
    )
    assert query == (
        "select from people\n"
        "where\n"
        '  clay.filter_to_companies(("stripe.com", "openai.com"))\n'
        '  and experiences.any(is_current = true and job_title is_similar_to ("Chief Medical Officer"))'
    )


def test_domain_query_keeps_the_exclusion_inside_experiences_any():
    query = build_people_query_for_domains(
        ["acme.com"], ["engineer"], job_title_exclude=["intern"]
    )
    assert query == (
        "select from people\n"
        "where\n"
        '  clay.filter_to_companies(("acme.com"))\n'
        '  and experiences.any(is_current = true and job_title is_similar_to ("engineer") '
        'and not job_title is_similar_to ("intern"))'
    )
