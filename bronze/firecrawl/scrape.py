"""Calls Firecrawl.dev's /scrape endpoint directly and returns exactly the
two fields this repo's own Firecrawl pipeline needs.

Response shape confirmed live against docs.firecrawl.dev, 2026-09-08:
    {"success": true, "data": {"markdown": "...",
                                "metadata": {"sourceURL": "...", "title": "...", "statusCode": 200}}}

PLACEHOLDER - not yet wired into anything. Intended use once connected:

    from bronze.firecrawl.scrape import scrape_url
    from silver.firecrawl import Firecrawl

    fetched = scrape_url("https://example.com")
    row = Firecrawl().run_all(fetched["markdown"], source_url=fetched["source_url"])

`source_url` here is `data.metadata.sourceURL` - exactly the
context["source_url"] input silver/firecrawl/datapoints/domain_normalize.py
requires (context-only since the 2026-09-08 fix, no markdown-guessing
fallback), so this return value can be handed straight to Firecrawl.run_all()
without any reshaping.
"""
from typing import Any, Dict, Sequence

from . import _http

DEFAULT_FORMATS: Sequence[str] = ("markdown",)


def scrape_url(url: str, formats: Sequence[str] = DEFAULT_FORMATS) -> Dict[str, Any]:
    """Returns {"markdown": str | None, "source_url": str, "title": str | None,
    "status_code": int | None}. Falls back to the requested `url` for
    source_url if Firecrawl's response omits metadata (defensive - not
    observed in practice, but domain_normalize needs *something*)."""
    response = _http.post("/scrape", {"url": url, "formats": list(formats)})
    data = response.get("data") or {}
    metadata = data.get("metadata") or {}
    return {
        "markdown": data.get("markdown"),
        "source_url": metadata.get("sourceURL") or url,
        "title": metadata.get("title"),
        "status_code": metadata.get("statusCode"),
    }
