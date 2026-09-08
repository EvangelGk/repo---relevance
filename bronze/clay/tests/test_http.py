"""Tests for bronze.clay._http's key-loading logic. Deliberately doesn't
touch the network - _request() itself (urlopen) is exercised indirectly
via search.py's mocked tests, since every real call goes through
urllib.request which this suite has no business hitting in CI."""
import pytest

from bronze.clay import _http


@pytest.fixture(autouse=True)
def _clear_key_env(monkeypatch):
    monkeypatch.delenv("CLAY_PUBLIC_API_KEY", raising=False)
    # Point at a nonexistent .env for these tests so the repo's real .env
    # (which may have a real key on a dev machine) never leaks in.
    monkeypatch.setattr(_http, "_ENV_PATH", "/does/not/exist/.env")


def test_missing_key_raises_clay_api_error():
    with pytest.raises(_http.ClayAPIError, match="CLAY_PUBLIC_API_KEY is not set"):
        _http._api_key()


def test_placeholder_key_raises_clay_api_error(monkeypatch):
    monkeypatch.setenv("CLAY_PUBLIC_API_KEY", "paste-your-key-here")
    with pytest.raises(_http.ClayAPIError, match="CLAY_PUBLIC_API_KEY is not set"):
        _http._api_key()


def test_real_looking_key_is_returned(monkeypatch):
    monkeypatch.setenv("CLAY_PUBLIC_API_KEY", "clay_abc123")
    assert _http._api_key() == "clay_abc123"


def test_falls_back_to_parsing_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nCLAY_PUBLIC_API_KEY=clay_from_file\n", encoding="utf-8")
    monkeypatch.setattr(_http, "_ENV_PATH", str(env_file))
    assert _http._api_key() == "clay_from_file"
