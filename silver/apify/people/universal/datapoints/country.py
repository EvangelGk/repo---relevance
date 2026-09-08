"""extract_country(raw_apify_person: dict) -> str | None"""
from typing import Any, Dict, Optional

from ._common import first


def extract_country(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_person or {}
    return first(raw, "country", "addressCountryOnly", "location")
