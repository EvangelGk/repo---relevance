"""load_apify_company_records(raw) -> list[dict]

Apify's own actor datasets export as a JSON array of item dicts (one per
scraped company) - the standard Apify dataset-export shape
(`{"items": [...]}` for some endpoints, a bare `[...]` for others, or a
single `{...}` record for a one-off item). This loader's only job is
turning that raw JSON - a file path or an already-parsed object - into a
flat `list[dict]`, one dict per company record; it does no field mapping
itself (that's `extract.py`'s job, one call to
`extract_company_universal_fields()` per item this returns).

Kept separate from `extract.py` for the same reason
`silver/prospeo/people/universal/loader.py` is separate from whatever
eventually maps its columns: reading/parsing a source's raw file format is
a different concern from mapping its fields, and each source's raw shape
(Apify JSON array, Firecrawl JSON response, Prospeo CSV) is different
enough to deserve its own small loader rather than one shared "read
anything" utility.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Union


def load_apify_company_records(raw: Union[str, Path, dict, list]) -> List[Dict[str, Any]]:
    if isinstance(raw, (str, Path)):
        with open(raw, "r", encoding="utf-8") as f:
            raw = json.load(f)

    if isinstance(raw, dict):
        items = raw.get("items")
        if items is None:
            items = raw.get("data")
        if items is None:
            items = [raw]
        raw = items

    if not isinstance(raw, list):
        raise ValueError(f"expected a JSON array (or {{'items': [...]}}) of company records, got {type(raw)}")

    return raw
