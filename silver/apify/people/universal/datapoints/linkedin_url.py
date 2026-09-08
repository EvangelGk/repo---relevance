"""extract_linkedin_url(raw_apify_person: dict) -> str | None

The person's own LinkedIn profile URL, straight off the raw Apify record.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_linkedin_url(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_person or {}
    return first(raw, "linkedin_url", "linkedinUrl", "profileUrl", "url")
