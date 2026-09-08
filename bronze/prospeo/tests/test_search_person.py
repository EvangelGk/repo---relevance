"""Tests for bronze.prospeo.search_person - HTTP is mocked throughout
(patching bronze.prospeo.search_person._http.post), no real network call."""
from unittest.mock import patch

from bronze.prospeo.search_person import search_person


def test_job_title_include_builds_person_job_title_filter():
    with patch("bronze.prospeo.search_person._http.post", return_value={}) as mock_post:
        search_person(job_title_include=["account executive"])

    mock_post.assert_called_once_with(
        "/search-person",
        {"page": 1, "person_job_title": {"match_mode": "CONTAINS", "include": ["account executive"]}},
    )


def test_job_title_include_and_exclude_both_present():
    with patch("bronze.prospeo.search_person._http.post", return_value={}) as mock_post:
        search_person(job_title_include=["VP Sales"], job_title_exclude=["assistant"])

    _, body = mock_post.call_args[0]
    assert body["person_job_title"] == {
        "match_mode": "CONTAINS",
        "include": ["VP Sales"],
        "exclude": ["assistant"],
    }


def test_no_job_title_filter_when_neither_include_nor_exclude_given():
    with patch("bronze.prospeo.search_person._http.post", return_value={}) as mock_post:
        search_person(page=2)

    mock_post.assert_called_once_with("/search-person", {"page": 2})


def test_extra_filters_pass_through_verbatim():
    with patch("bronze.prospeo.search_person._http.post", return_value={}) as mock_post:
        search_person(job_title_include=["CTO"], company_size={"include": ["51-200"]})

    _, body = mock_post.call_args[0]
    assert body["company_size"] == {"include": ["51-200"]}


def test_returns_raw_response_unmodified():
    fake_response = {"results": [{"person_id": "p1"}], "pagination": {"page": 1}}
    with patch("bronze.prospeo.search_person._http.post", return_value=fake_response):
        result = search_person(job_title_include=["CEO"])

    assert result == fake_response
