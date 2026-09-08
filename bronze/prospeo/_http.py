"""Thin authenticated HTTP client for Prospeo's API
(https://api.prospeo.io, auth/endpoint shape confirmed live against
prospeo.io/api-docs, 2026-09-08).

Called directly, no Clay relay - for search_person specifically, Clay's
own native Prospeo integration only covers Prospeo's email-finder/
enrichment endpoints, not the Search Person discovery endpoint (see the
terminal discussion: Clay's Prospeo docs describe enrichment-of-a-known-
person, billed through Clay's own credits; Search Person is a separate,
Prospeo-only proprietary dataset, the same category as Clay's own company
search rather than a relay-able single utility call).

Same shape as bronze/clay|firecrawl|apify's _http.py (stdlib urllib only,
.env fallback anchored to this file's own location, same error hierarchy)
- duplicated rather than shared, matching this repo's existing per-module
style. One real difference: Prospeo authenticates via a plain `X-KEY`
header, not `Authorization: Bearer` (Firecrawl/Apify) or `clay-api-key`
(Clay) - three different vendors, three different header names, so this
isn't unified into a shared helper.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = "https://api.prospeo.io"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")

_PLACEHOLDER_KEY = "paste-your-key-here"


class ProspeoAPIError(RuntimeError):
    """Raised for any non-2xx response from Prospeo's API, or a
    missing/placeholder API key. Note: per Prospeo's own docs, HTTP 400
    covers both an invalid API key AND an otherwise malformed request body
    - inspect `.body` to tell which."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Prospeo API returned HTTP {status}: {body[:500]}")


class ProspeoRateLimited(ProspeoAPIError):
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
    if "PROSPEO_API_KEY" not in os.environ:
        _load_env_file()
    key = os.environ.get("PROSPEO_API_KEY", "")
    if not key or key == _PLACEHOLDER_KEY:
        raise ProspeoAPIError(0, "PROSPEO_API_KEY is not set - see .env.example")
    return key


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-KEY", _api_key())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise ProspeoRateLimited(exc.code, response_body) from exc
        raise ProspeoAPIError(exc.code, response_body) from exc


def get(path: str) -> Dict[str, Any]:
    return _request("GET", path)


def post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return _request("POST", path, body)
