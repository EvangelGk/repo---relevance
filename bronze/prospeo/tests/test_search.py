"""Tests for bronze.prospeo.search.run_people_search_for_company - HTTP is
mocked throughout (patching bronze.prospeo.search_person._http.post), no
real network call."""
from unittest.mock import patch

from bronze.prospeo.search import run_people_search_for_company
from client_context.schema import ClientContext


def _context(**overrides) -> ClientContext:
    defaults = {
        "client_id": "test",
        "name": "Test",
        "people_job_title_include": ["VP Sales"],
    }
    defaults.update(overrides)
    return ClientContext(**defaults)


def test_no_job_title_filter_skips_the_call_entirely():
    with patch("bronze.prospeo.search_person._http.post") as mock_post:
        result = run_people_search_for_company({"domain": "acme.com"}, _context(people_job_title_include=()))

    mock_post.assert_not_called()
    assert result == {"people": [], "matched_by": None}


def test_domain_match_used_when_it_returns_results():
    fake_response = {"results": [{"person_id": "p1"}, {"person_id": "p2"}]}
    with patch("bronze.prospeo.search_person._http.post", return_value=fake_response) as mock_post:
        result = run_people_search_for_company({"domain": "acme.com", "name": "Acme"}, _context())

    _, body = mock_post.call_args[0]
    assert body["company_website"] == "acme.com"
    assert "company_name" not in body
    assert result == {"people": [{"person_id": "p1"}, {"person_id": "p2"}], "matched_by": "domain"}


def test_falls_back_to_name_when_domain_match_returns_nothing():
    empty_then_hit = [{"results": []}, {"results": [{"person_id": "p1"}]}]
    with patch("bronze.prospeo.search_person._http.post", side_effect=empty_then_hit) as mock_post:
        result = run_people_search_for_company({"domain": "acme.com", "name": "Acme"}, _context())

    assert mock_post.call_count == 2
    _, second_body = mock_post.call_args_list[1][0]
    assert second_body["company_name"] == "Acme"
    assert result == {"people": [{"person_id": "p1"}], "matched_by": "name"}


def test_no_domain_or_name_returns_empty_without_calling_prospeo():
    with patch("bronze.prospeo.search_person._http.post") as mock_post:
        result = run_people_search_for_company({}, _context())

    mock_post.assert_not_called()
    assert result == {"people": [], "matched_by": None}


def test_results_capped_at_people_max_per_company():
    fake_response = {"results": [{"person_id": str(i)} for i in range(10)]}
    with patch("bronze.prospeo.search_person._http.post", return_value=fake_response):
        result = run_people_search_for_company(
            {"domain": "acme.com"}, _context(people_max_per_company=3)
        )

    assert len(result["people"]) == 3
    assert result["matched_by"] == "domain"
