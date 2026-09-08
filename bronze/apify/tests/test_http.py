"""Tests for bronze.apify._http's token-loading logic - same shape as
bronze/clay/tests/test_http.py. No network calls."""
import pytest

from bronze.apify import _http


@pytest.fixture(autouse=True)
def _clear_token_env(monkeypatch):
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
    monkeypatch.setattr(_http, "_ENV_PATH", "/does/not/exist/.env")


def test_missing_token_raises_apify_api_error():
    with pytest.raises(_http.ApifyAPIError, match="APIFY_API_TOKEN is not set"):
        _http._api_token()


def test_placeholder_token_raises_apify_api_error(monkeypatch):
    monkeypatch.setenv("APIFY_API_TOKEN", "paste-your-token-here")
    with pytest.raises(_http.ApifyAPIError, match="APIFY_API_TOKEN is not set"):
        _http._api_token()


def test_real_looking_token_is_returned(monkeypatch):
    monkeypatch.setenv("APIFY_API_TOKEN", "apify_api_abc123")
    assert _http._api_token() == "apify_api_abc123"


def test_falls_back_to_parsing_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("APIFY_API_TOKEN=apify_api_from_file\n", encoding="utf-8")
    monkeypatch.setattr(_http, "_ENV_PATH", str(env_file))
    assert _http._api_token() == "apify_api_from_file"
