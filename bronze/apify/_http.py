"""Thin authenticated HTTP client for Apify's API
(https://api.apify.com/v2, auth/endpoint shape confirmed live against
docs.apify.com 2026-09-08).

Called directly, no Clay relay - same reasoning as bronze/firecrawl: a
specific actor is a single-vendor, no-waterfall call, so a Clay hop adds
an extra round trip and a real storage ceiling for zero benefit.

Same shape as bronze/clay/_http.py and bronze/firecrawl/_http.py (stdlib
urllib only, .env fallback anchored to this file's own location, same
error hierarchy) - duplicated rather than shared, matching this repo's
existing per-module style.

One real difference from the other two clients: Apify's
run-sync-get-dataset-items endpoint (see run_actor.py) returns a bare JSON
*array* at the top level, not an object - so `post`/`get` here return
`Any`, not `Dict[str, Any]`, unlike the other two bronze/*/_http.py clients.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = "https://api.apify.com/v2"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")

_PLACEHOLDER_TOKEN = "paste-your-token-here"


class ApifyAPIError(RuntimeError):
    """Raised for any non-2xx response from Apify's API, or a
    missing/placeholder API token."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Apify API returned HTTP {status}: {body[:500]}")


class ApifyRateLimited(ApifyAPIError):
    """HTTP 429 - back off and retry."""


class ApifyRunTimedOut(ApifyAPIError):
    """HTTP 408 - the actor didn't finish within the requested synchronous
    timeout. Longer-running actors need the async run + poll + fetch-
    dataset flow instead, which this module doesn't implement yet
    (placeholder scope - see run_actor.py's docstring)."""


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


def _api_token() -> str:
    if "APIFY_API_TOKEN" not in os.environ:
        _load_env_file()
    token = os.environ.get("APIFY_API_TOKEN", "")
    if not token or token == _PLACEHOLDER_TOKEN:
        raise ApifyAPIError(0, "APIFY_API_TOKEN is not set - see .env.example")
    return token


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {_api_token()}")
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=310) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 408:
            raise ApifyRunTimedOut(exc.code, response_body) from exc
        if exc.code == 429:
            raise ApifyRateLimited(exc.code, response_body) from exc
        raise ApifyAPIError(exc.code, response_body) from exc


def get(path: str) -> Any:
    return _request("GET", path)


def post(path: str, body: Optional[Dict[str, Any]] = None) -> Any:
    return _request("POST", path, body)
