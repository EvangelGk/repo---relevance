"""Prospeo's Enrich Person endpoint - reveals the email/mobile that
search_person.py's results always leave masked. Separate, higher-cost call
by design (1 credit/email, 10 credits/mobile - mobile reveal includes
email at no extra cost) - see search_person.py's docstring for the
search-then-gate-then-enrich discipline this split is meant to support.

PLACEHOLDER: not yet wired into anything that decides WHICH search_person
results are worth enriching - that gate belongs one layer up (a
ClientContext-driven filter, or an orchestrator-style check), not in this
module.
"""
from typing import Any, Dict, Optional

from . import _http


def enrich_person(
    person_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    only_verified_email: bool = True,
) -> Dict[str, Any]:
    """Reveals one person's contact details. Pass `person_id` to enrich a
    specific result from search_person() - the natural continuation of a
    search; pass `data` (e.g. {"first_name", "last_name", "company"}) to
    enrich from raw identity fields without a prior search, per Prospeo's
    documented request shape. `only_verified_email` (default True) skips
    charging for an unverified/low-confidence email match."""
    body: Dict[str, Any] = {"only_verified_email": only_verified_email}
    if person_id:
        body["person_id"] = person_id
    if data:
        body["data"] = data
    return _http.post("/enrich-person", body)
