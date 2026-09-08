"""Thin authenticated HTTP client for Clay's public developer API
(https://api.clay.com/public/v0, fetched/confirmed live 2026-09-08).

Zero third-party HTTP dependency on purpose - this repo doesn't have one
yet (see pyproject.toml), and adding `requests` just for this one client
would mean a poetry lock/install round-trip before any of this could even
be tried. stdlib urllib.request is enough for the request volume a
client-context-driven search does. Swap to `requests`/httpx later if
bronze/ grows enough call sites that the stdlib boilerplate starts to hurt.

Reads CLAY_PUBLIC_API_KEY from the process environment; falls back to
parsing the repo root's .env directly (KEY=VALUE lines, no third-party
dotenv dependency, for the same "no new dep for one small thing" reason
above) if the process environment doesn't already have it - so a plain
`python -m bronze.clay...` invocation works without requiring the caller
to `source .env` first. This mirrors dead_letter.py/drift.py's existing
pattern of anchoring a default path to this module's own file location
rather than the caller's cwd.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

BASE_URL = "https://api.clay.com/public/v0"

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")

_PLACEHOLDER_KEY = "paste-your-key-here"


class ClayAPIError(RuntimeError):
    """Raised for any non-2xx response from Clay's public API, or a
    missing/placeholder API key."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Clay API returned HTTP {status}: {body[:500]}")


class ClayBudgetExhausted(ClayAPIError):
    """HTTP 402 - Data Credits/Actions budget exhausted. Treat as a hard
    stop for the whole batch, not a per-row retry - retrying just spends
    the same exhausted budget again."""


class ClayRateLimited(ClayAPIError):
    """HTTP 429 - back off and retry. Callers doing more than a handful of
    requests should add real backoff; this module doesn't retry on its
    own so a caller can choose its own policy."""


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
    if "CLAY_PUBLIC_API_KEY" not in os.environ:
        _load_env_file()
    key = os.environ.get("CLAY_PUBLIC_API_KEY", "")
    if not key or key == _PLACEHOLDER_KEY:
        raise ClayAPIError(0, "CLAY_PUBLIC_API_KEY is not set - see .env.example")
    return key


def _request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("clay-api-key", _api_key())
    if data is not None:
        req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 402:
            raise ClayBudgetExhausted(exc.code, response_body) from exc
        if exc.code == 429:
            raise ClayRateLimited(exc.code, response_body) from exc
        raise ClayAPIError(exc.code, response_body) from exc


def get(path: str) -> Dict[str, Any]:
    return _request("GET", path)


def post(path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return _request("POST", path, body)
