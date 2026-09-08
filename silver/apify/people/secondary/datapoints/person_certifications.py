"""function_person_certifications(raw_certifications: list[dict] | None) -> list[dict]

People-side conceptual analog of Firecrawl's `compliance_framework_extract`
(silver/firecrawl/datapoints/compliance_framework_extract.py) - built fresh
here rather than copied, since Firecrawl only ever processes company-website
markdown in this repo and structurally cannot run against a LinkedIn/Apify
person row.

Source: Apify's LinkedIn "Certifications and Dates" profile section. The
exact key names an Apify actor uses for this array are UNCONFIRMED (no live
sample pulled in this session), so this function accepts several plausible
per-entry key spellings rather than guessing one and normalizes them to a
single output shape:

    [{"name": str, "issuer": str | None, "issued_date": str | None}, ...]

Accepted input per-entry keys (first match wins, checked in this order):
  name:        "name", "title", "certification"
  issuer:      "issuer", "authority", "organization"
  issued_date: "issued_date", "issue_date", "date"

Entries missing a name are dropped - a certification with no name is not
usable signal.
"""
from typing import Any, Dict, List, Optional

_NAME_KEYS = ("name", "title", "certification")
_ISSUER_KEYS = ("issuer", "authority", "organization")
_DATE_KEYS = ("issued_date", "issue_date", "date")


def _first_present(entry: Dict[str, Any], keys) -> Optional[Any]:
    for key in keys:
        if entry.get(key):
            return entry[key]
    return None


def function_person_certifications(raw_certifications: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    entries = raw_certifications or []
    result = []
    for entry in entries:
        name = _first_present(entry, _NAME_KEYS)
        if not name:
            continue
        result.append({
            "name": str(name).strip(),
            "issuer": _first_present(entry, _ISSUER_KEYS),
            "issued_date": _first_present(entry, _DATE_KEYS),
        })
    return result
