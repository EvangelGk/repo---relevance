"""load_apify_person_records(raw) -> list[dict]

Same shape and same reasoning as
`silver/apify/company/universal/loader.py` - see that module's docstring.
This is the person-side twin: turns Apify's raw JSON dataset export (file
path or already-parsed object) into a flat `list[dict]`, one dict per
scraped LinkedIn person record. No field mapping here - that's
`extract.py`'s job, one call to `extract_person_universal_fields()` per
item this returns.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Union


def load_apify_person_records(raw: Union[str, Path, dict, list]) -> List[Dict[str, Any]]:
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
        raise ValueError(f"expected a JSON array (or {{'items': [...]}}) of person records, got {type(raw)}")

    return raw
