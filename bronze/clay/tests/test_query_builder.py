"""Tests for bronze.clay.query_builder - pure string-building, no network.
Each test pins one ClientContext field to one exact DSL clause, cross-
referenced against Clay's live query-mode/reference doc (fetched
2026-09-08) rather than an assumed shape."""
from client_context.schema import ClientContext
from bronze.clay.query_builder import build_company_query


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


def test_technologies_check_both_vendor_and_product_subfields():
    query = build_company_query(_context(technologies=("Salesforce",)))
    assert 'technographics.any(vendor = "Salesforce" or product = "Salesforce")' in query


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
