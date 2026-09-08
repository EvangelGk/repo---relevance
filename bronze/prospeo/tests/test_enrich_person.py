"""Tests for bronze.prospeo.enrich_person - HTTP is mocked throughout
(patching bronze.prospeo.enrich_person._http.post), no real network call."""
from unittest.mock import patch

from bronze.prospeo.enrich_person import enrich_person


def test_enrich_by_person_id():
    with patch("bronze.prospeo.enrich_person._http.post", return_value={}) as mock_post:
        enrich_person(person_id="p1")

    mock_post.assert_called_once_with(
        "/enrich-person", {"only_verified_email": True, "person_id": "p1"}
    )


def test_enrich_by_raw_data():
    data = {"first_name": "John", "last_name": "Doe", "company": "acme.com"}
    with patch("bronze.prospeo.enrich_person._http.post", return_value={}) as mock_post:
        enrich_person(data=data)

    mock_post.assert_called_once_with(
        "/enrich-person", {"only_verified_email": True, "data": data}
    )


def test_only_verified_email_can_be_disabled():
    with patch("bronze.prospeo.enrich_person._http.post", return_value={}) as mock_post:
        enrich_person(person_id="p1", only_verified_email=False)

    mock_post.assert_called_once_with(
        "/enrich-person", {"only_verified_email": False, "person_id": "p1"}
    )


def test_returns_raw_response_unmodified():
    fake_response = {"email": "john@acme.com", "mobile": None}
    with patch("bronze.prospeo.enrich_person._http.post", return_value=fake_response):
        result = enrich_person(person_id="p1")

    assert result == fake_response
