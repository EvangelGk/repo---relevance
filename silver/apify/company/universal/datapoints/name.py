"""extract_name(raw_apify_company: dict) -> str | None

Company display name, straight off the raw Apify LinkedIn company record.
Field-name map assumes common Apify LinkedIn company-actor conventions -
CONFIRM against a real sample before production use (no live Apify
integration exists yet in this repo).
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_name(raw_apify_company: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_company or {}
    return first(raw, "name", "companyName", "companyname")
