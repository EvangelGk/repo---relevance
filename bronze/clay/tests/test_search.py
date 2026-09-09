"""Tests for bronze.clay.search - HTTP is mocked throughout (patching
bronze.clay.search._http.post) so this suite never makes a real network
call, matching this repo's existing offline-test convention."""
from unittest.mock import patch

from client_context.schema import ClientContext
from bronze.clay.search import (
    run_company_search,
    run_people_search,
    run_people_search_for_domains,
)


def _context(**overrides) -> ClientContext:
    defaults = {"client_id": "test", "name": "Test", "limit": 100}
    defaults.update(overrides)
    return ClientContext(**defaults)


def test_single_page_result():
    responses = [
        {"search_id": "s1", "source_type": "companies"},
        {"data": [{"domain": "acme.com"}, {"domain": "beta.com"}], "has_more": False},
    ]
    with patch("bronze.clay.search._http.post", side_effect=responses) as mock_post:
        result = run_company_search(_context())

    assert result["companies"] == [{"domain": "acme.com"}, {"domain": "beta.com"}]
    assert result["source_type"] == "companies"
    assert result["query"] == "select from companies"
    assert mock_post.call_count == 2
    mock_post.assert_any_call("/search/query-mode", {"query": "select from companies"})
    mock_post.assert_any_call("/search/query-mode/s1/run", {"limit": 100})


def test_pages_until_has_more_is_false():
    responses = [
        {"search_id": "s1", "source_type": "companies"},
        {"data": [{"domain": f"c{i}.com"} for i in range(5)], "has_more": True},
        {"data": [{"domain": "last.com"}], "has_more": False},
    ]
    with patch("bronze.clay.search._http.post", side_effect=responses) as mock_post:
        result = run_company_search(_context(limit=6))

    assert len(result["companies"]) == 6
    assert result["companies"][-1] == {"domain": "last.com"}
    assert mock_post.call_count == 3


def test_stops_once_requested_limit_is_reached_even_if_more_remain():
    responses = [
        {"search_id": "s1", "source_type": "companies"},
        {"data": [{"domain": f"c{i}.com"} for i in range(5)], "has_more": True},
    ]
    with patch("bronze.clay.search._http.post", side_effect=responses) as mock_post:
        result = run_company_search(_context(limit=5))

    assert len(result["companies"]) == 5
    # Only the create call + one run call - the loop stops because
    # `remaining` hit 0, not because it ran out of retries.
    assert mock_post.call_count == 2


def test_empty_first_page_stops_the_loop_even_if_has_more_is_true():
    """Defensive: a malformed/empty page with has_more=True must not spin
    forever - `not page` breaks the loop regardless of has_more."""
    responses = [
        {"search_id": "s1", "source_type": "companies"},
        {"data": [], "has_more": True},
    ]
    with patch("bronze.clay.search._http.post", side_effect=responses):
        result = run_company_search(_context())

    assert result["companies"] == []


def test_people_search_skips_the_api_call_with_no_job_title_filter():
    with patch("bronze.clay.search._http.post") as mock_post:
        result = run_people_search(_context())

    mock_post.assert_not_called()
    assert result == {"people": [], "source_type": None, "query": None}


def test_people_search_runs_the_same_create_and_paginate_flow():
    responses = [
        {"search_id": "s1", "source_type": "people"},
        {"data": [{"full_name": "Ada Lovelace"}], "has_more": False},
    ]
    context = _context(people_job_title_include=("VP Sales",))
    with patch("bronze.clay.search._http.post", side_effect=responses) as mock_post:
        result = run_people_search(context)

    assert result["people"] == [{"full_name": "Ada Lovelace"}]
    assert result["source_type"] == "people"
    assert result["query"] == (
        "select from people\n"
        "where\n"
        '  experiences.any(is_current = true and job_title is_similar_to ("VP Sales"))'
    )
    mock_post.assert_any_call("/search/query-mode", {"query": result["query"]})
    mock_post.assert_any_call("/search/query-mode/s1/run", {"limit": 100})


def test_people_search_for_domains_skips_the_api_call_with_no_domains():
    with patch("bronze.clay.search._http.post") as mock_post:
        result = run_people_search_for_domains([], ["VP Sales"])

    mock_post.assert_not_called()
    assert result == {"people": [], "source_type": None, "query": None}


def test_people_search_for_domains_uses_filter_to_companies():
    responses = [
        {"search_id": "s1", "source_type": "people"},
        {"data": [{"full_name": "Ada Lovelace"}], "has_more": False},
    ]
    with patch("bronze.clay.search._http.post", side_effect=responses) as mock_post:
        result = run_people_search_for_domains(
            ["novartis.com"], ["Chief Medical Officer"], limit=50
        )

    assert result["people"] == [{"full_name": "Ada Lovelace"}]
    assert result["query"] == (
        "select from people\n"
        "where\n"
        '  clay.filter_to_companies(("novartis.com"))\n'
        '  and experiences.any(is_current = true and job_title is_similar_to ("Chief Medical Officer"))'
    )
    mock_post.assert_any_call("/search/query-mode/s1/run", {"limit": 50})
