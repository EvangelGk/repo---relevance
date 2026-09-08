"""extract_full_name(raw_apify_person: dict) -> str | None

Prefers a flat full-name field; falls back to joining firstName/lastName
when Apify's actor only returns split name fields.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_full_name(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[str]:
    raw = raw_apify_person or {}
    full_name = first(raw, "full_name", "fullName", "name")
    if full_name is None:
        first_name, last_name = raw.get("firstName"), raw.get("lastName")
        if first_name or last_name:
            full_name = " ".join(p for p in (first_name, last_name) if p)
    return full_name
