"""Thin authenticated HTTP client for Firecrawl.dev's scrape API
(https://api.firecrawl.dev/v2, auth/response shape confirmed live against
docs.firecrawl.dev 2026-09-08).

Called directly, no Clay relay - see the terminal discussion: Firecrawl is
a single-vendor, no-waterfall fetch (unlike a Clay-managed enrichment,
there's no second provider to fail over to), so routing it through a Clay
function added an extra hop and a real storage ceiling - 8,000 chars for a
basic/formula column, 200KB for an action column - for zero benefit. This
module has neither limit.

Same shape as bronze/clay/_http.py (stdlib urllib only, .env fallback
anchored to this file's own location, same error hierarchy) - duplicated
rather than shared, matching this repo's existing per-module style (see
datapoints/*.py, each self-contained).
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = "https://api.firecrawl.dev/v2"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")

_PLACEHOLDER_KEY = "paste-your-key-here"


class FirecrawlAPIError(RuntimeError):
    """Raised for any non-2xx response from Firecrawl's API, or a
    missing/placeholder API key."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Firecrawl API returned HTTP {status}: {body[:500]}")


class FirecrawlRateLimited(FirecrawlAPIError):
    """HTTP 429 - back off and retry."""


def _load_env_file() -> None:
    if not os.path.exists(_ENV_PATH):
        return
    with open(_ENV_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def _api_key() -> str:
    if "FIRECRAWL_API_KEY" not in os.environ:
        _load_env_file()
    key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not key or key == _PLACEHOLDER_KEY:
        raise FirecrawlAPIError(0, "FIRECRAWL_API_KEY is not set - see .env.example")
    return key


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_api_key()}")
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise FirecrawlRateLimited(exc.code, response_body) from exc
        raise FirecrawlAPIError(exc.code, response_body) from exc


def get(path: str) -> Dict[str, Any]:
    return _request("GET", path)


def post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return _request("POST", path, body)
