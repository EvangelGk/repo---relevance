"""Tests for bronze.apify.run_actor - HTTP is mocked throughout (patching
bronze.apify.run_actor._http.post), no real network call."""
from unittest.mock import patch

from bronze.apify.run_actor import run_actor


def test_returns_dataset_items_list_as_is():
    items = [{"domain": "acme.com"}, {"domain": "beta.com"}]
    with patch("bronze.apify.run_actor._http.post", return_value=items) as mock_post:
        result = run_actor("janedoe~my-actor", {"query": "b2b saas"})

    assert result == items
    mock_post.assert_called_once_with(
        "/acts/janedoe~my-actor/run-sync-get-dataset-items?timeout=300",
        {"query": "b2b saas"},
    )


def test_custom_timeout_is_passed_through():
    with patch("bronze.apify.run_actor._http.post", return_value=[]) as mock_post:
        run_actor("some-actor-id", timeout_seconds=60)

    mock_post.assert_called_once_with(
        "/acts/some-actor-id/run-sync-get-dataset-items?timeout=60", {}
    )


def test_non_list_response_returns_empty_list_defensively():
    """The dataset-items endpoint is documented to return a bare array;
    if Apify ever wraps it differently, fail safe to empty rather than
    crash or silently return an unexpected shape."""
    with patch("bronze.apify.run_actor._http.post", return_value={"unexpected": "shape"}):
        result = run_actor("some-actor-id")

    assert result == []
