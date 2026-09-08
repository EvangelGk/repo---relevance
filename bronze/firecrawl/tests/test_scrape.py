"""Tests for bronze.firecrawl.scrape - HTTP is mocked throughout (patching
bronze.firecrawl.scrape._http.post), no real network call."""
from unittest.mock import patch

from bronze.firecrawl.scrape import scrape_url


def test_maps_data_markdown_and_source_url():
    fake_response = {
        "success": True,
        "data": {
            "markdown": "# Acme\n\nAcme Corp builds widgets.",
            "metadata": {"sourceURL": "https://acme.com", "title": "Acme", "statusCode": 200},
        },
    }
    with patch("bronze.firecrawl.scrape._http.post", return_value=fake_response) as mock_post:
        result = scrape_url("https://acme.com")

    assert result == {
        "markdown": "# Acme\n\nAcme Corp builds widgets.",
        "source_url": "https://acme.com",
        "title": "Acme",
        "status_code": 200,
    }
    mock_post.assert_called_once_with(
        "/scrape", {"url": "https://acme.com", "formats": ["markdown"]}
    )


def test_falls_back_to_requested_url_when_metadata_is_missing():
    fake_response = {"success": True, "data": {"markdown": "content"}}
    with patch("bronze.firecrawl.scrape._http.post", return_value=fake_response):
        result = scrape_url("https://acme.com")

    assert result["source_url"] == "https://acme.com"
    assert result["title"] is None
    assert result["status_code"] is None


def test_custom_formats_are_passed_through():
    with patch(
        "bronze.firecrawl.scrape._http.post",
        return_value={"success": True, "data": {}},
    ) as mock_post:
        scrape_url("https://acme.com", formats=("markdown", "html"))

    mock_post.assert_called_once_with(
        "/scrape", {"url": "https://acme.com", "formats": ["markdown", "html"]}
    )
