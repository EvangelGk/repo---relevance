"""extract_markdown_and_source_url(raw) -> {"markdown": str | None, "source_url": str | None}

New file, additive - does not touch `firecrawl.py` or anything under
`datapoints/`. Firecrawl's actual scrape API returns a JSON document, not
a bare markdown string - typically `{"markdown": "...", "metadata":
{"sourceURL": "...", ...}}`, sometimes nested one level deeper as
`{"data": {"markdown": ..., "metadata": {...}}}` depending on which
endpoint/SDK version produced it. This repo's `Firecrawl` class
(`firecrawl.py`) is deliberately "pure execution" over already-extracted
markdown text - it has no format-parsing concerns and shouldn't grow any.
This loader is the seam between the two: given the raw JSON Firecrawl (the
service) hands back - a file path or an already-parsed dict - it pulls out
the `(markdown, source_url)` pair that feeds directly into
`Firecrawl.run_all(markdown, source_url=source_url)` /
`SilverOrchestrator.process_page(markdown, {"source_url": source_url})`.

Same reasoning as the Apify loaders in `apify/company/universal/loader.py`
and `apify/people/universal/loader.py`: reading/parsing a source's raw
file format is a different concern from what the extractor does with the
content, so it gets its own small file rather than being folded into
`firecrawl.py`.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union


def load_firecrawl_json(raw: Union[str, Path, dict]) -> dict:
    if isinstance(raw, (str, Path)):
        with open(raw, "r", encoding="utf-8") as f:
            raw = json.load(f)
    return raw


def extract_markdown_and_source_url(raw: Union[str, Path, dict]) -> Dict[str, Optional[str]]:
    data: Dict[str, Any] = load_firecrawl_json(raw)

    # Some Firecrawl responses nest the real payload under "data"
    # (the /scrape v1 API shape); others put markdown/metadata at the
    # top level directly (older API versions, or an actor's own export).
    payload = data.get("data") if isinstance(data.get("data"), dict) else data

    markdown = payload.get("markdown")
    metadata = payload.get("metadata") or {}
    source_url = metadata.get("sourceURL") or metadata.get("url") or payload.get("sourceURL")

    return {"markdown": markdown, "source_url": source_url}
