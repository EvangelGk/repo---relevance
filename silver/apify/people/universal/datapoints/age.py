"""extract_age(raw_apify_person: dict) -> int | None

Raw age off the Apify LinkedIn person record, if the actor in use happens
to supply one.

**Caveat, not a guarantee**: LinkedIn does not publicly expose a member's
birthdate or age on the profile itself - there is no page element for a
scraper to read it off of. This extractor exists for actors that compute
or attach an estimated age from a separate source, following the same
"try the plausible key names, confirm against a real sample" convention
`job_title.py`/`country.py` already use; expect this to be `None` for most
real profiles rather than treat that as a bug.
"""
from typing import Any, Dict, Optional

from ._common import first


def extract_age(raw_apify_person: Optional[Dict[str, Any]]) -> Optional[Any]:
    raw = raw_apify_person or {}
    return first(raw, "age", "estimatedAge")
