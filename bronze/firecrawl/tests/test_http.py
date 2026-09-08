"""Tests for bronze.firecrawl._http's key-loading logic - same shape as
bronze/clay/tests/test_http.py. No network calls."""
import pytest

from bronze.firecrawl import _http


@pytest.fixture(autouse=True)
def _clear_key_env(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    monkeypatch.setattr(_http, "_ENV_PATH", "/does/not/exist/.env")


def test_missing_key_raises_firecrawl_api_error():
    with pytest.raises(_http.FirecrawlAPIError, match="FIRECRAWL_API_KEY is not set"):
        _http._api_key()


def test_placeholder_key_raises_firecrawl_api_error(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "paste-your-key-here")
    with pytest.raises(_http.FirecrawlAPIError, match="FIRECRAWL_API_KEY is not set"):
        _http._api_key()


def test_real_looking_key_is_returned(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-abc123")
    assert _http._api_key() == "fc-abc123"


def test_falls_back_to_parsing_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("FIRECRAWL_API_KEY=fc-from-file\n", encoding="utf-8")
    monkeypatch.setattr(_http, "_ENV_PATH", str(env_file))
    assert _http._api_key() == "fc-from-file"
