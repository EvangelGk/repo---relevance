"""extract_linkedin_about(raw_apify_person: dict) -> str | None

The person's LinkedIn "About" free text - source text for
`apify/people/secondary/datapoints/topic_classify.py` and
`bio_entity_extract.py`.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_linkedin_about(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_person or {}
    return first(raw, "linkedin_about", "about", "summary")
