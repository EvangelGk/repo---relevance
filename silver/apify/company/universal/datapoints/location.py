"""extract_location(raw_apify_company: dict) -> str | None

The only real location/HQ source in this repo (no live Firecrawl
extractor produces one - `structured_data_extract` was removed, cleaned
markdown can't preserve schema.org JSON-LD). Apify LinkedIn company actors
often return a structured headquarter object (city/geographicArea/country)
rather than a flat string - preferred when present, joined into one
"City, Region, Country" string; falls back to a flat location-shaped key.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_location(raw_apify_company: Optional[Dict[str, Any]]) -> Optional[str]:
    raw = raw_apify_company or {}
    hq = raw.get("headquarter") or raw.get("headquarters")
    if isinstance(hq, dict):
        parts = [hq.get(k) for k in ("city", "geographicArea", "country") if hq.get(k)]
        if parts:
            return ", ".join(parts)
    return first(raw, "location", "hqLocation", "companyLocation")
