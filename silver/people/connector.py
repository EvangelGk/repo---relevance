"""assemble_person_row(apify_person, prospeo_person, raw_experience, source_link) -> dict

The `people/` connector: assembles one person row from Apify (universal
LinkedIn fields) and Prospeo (email + whatever else Prospeo's export
happens to carry). Today no person field has more than one candidate
source, so - like `company/connector.py` - this is pure static tagging,
not a merge; per the source-differentiator convention, if a field ever
gains a second candidate source, resolve with a foreman-style priority
function first, then tag the winner - no such function exists in this
repo yet, so that path isn't wired here.

**Fixed 2026-09-08**: `seniority` and `employed_company` were previously
read as flat keys straight off `apify_person`, which isn't real - Apify
never returns either directly. `seniority` is now derived from
`apify_person["job_title"]` via `function_seniority`
(`apify/people/secondary/datapoints/seniority.py`). `employed_company` is
derived from `raw_experience` (the person's raw LinkedIn work-history
array) via `function_experience_array_resolve`
(`apify/people/secondary/datapoints/experience_array_resolve.py`), picking the
current entry's `company` string - falls back to a flat
`apify_person["employed_company"]` key if `raw_experience` isn't supplied,
for callers that already resolved it upstream. Note this is a raw company
NAME string, not a resolved `company_id` -
`function_experience_array_resolve` does no entity resolution; wiring
person rows to a real `company_id` would need a further call into
`company_entity_resolve` (Firecrawl-side, company-scoped) on that name,
which isn't done here - open item, not solved by this connector.

Inputs:
  - `apify_person`: output of `apify/people/universal/extract.py`
    (`extract_person_universal_fields`) - a
    dict with `linkedin_url`, `full_name`, `job_title`, `country`,
    `linkedin_about` (all `_source: "apify"`), plus optionally a flat
    `employed_company` fallback key (see above).
  - `prospeo_person`: Prospeo export row - `email` (`_source: "prospeo"`)
    plus any other columns Prospeo happens to include, passed through
    rather than dropped, each getting its own `<field>_source: "prospeo"`
    tag.
  - `raw_experience`: optional raw LinkedIn work-history array (see
    `function_experience_array_resolve`'s docstring for the expected
    per-entry shape). When supplied, drives `employed_company` derivation.
  - `source_link`: stamped from ingestion/batch context, passed through
    with no companion tag - it *is* the provenance value.
"""
from typing import Any, Dict, List, Optional

from silver.apify.people.secondary.datapoints.experience_array_resolve import function_experience_array_resolve
from silver.apify.people.secondary.datapoints.seniority import function_seniority

_APIFY_UNIVERSAL_FIELDS = (
    "linkedin_url", "full_name", "job_title", "country", "linkedin_about",
)
_PROSPEO_KNOWN_FIELDS = ("email",)


def _derive_employed_company(
    apify_person: Dict[str, Any], raw_experience: Optional[List[Dict[str, Any]]]
) -> Optional[str]:
    if raw_experience:
        resolved = function_experience_array_resolve(raw_experience)
        for entry in resolved["experiences"]:
            if entry["is_current"]:
                return entry["company"]
        if resolved["experiences"]:
            return resolved["experiences"][-1]["company"]
    return apify_person.get("employed_company")


def assemble_person_row(
    apify_person: Optional[Dict[str, Any]],
    prospeo_person: Optional[Dict[str, Any]],
    raw_experience: Optional[List[Dict[str, Any]]] = None,
    source_link: Optional[str] = None,
) -> Dict[str, Any]:
    apify_person = apify_person or {}
    prospeo_person = prospeo_person or {}

    row: Dict[str, Any] = {}
    for field in _APIFY_UNIVERSAL_FIELDS:
        row[field] = apify_person.get(field)
        row[f"{field}_source"] = "apify"

    row["seniority"] = function_seniority(apify_person.get("job_title")) or apify_person.get("seniority")
    row["seniority_source"] = "apify"

    row["employed_company"] = _derive_employed_company(apify_person, raw_experience)
    row["employed_company_source"] = "apify"

    for field, value in prospeo_person.items():
        row[field] = value
        row[f"{field}_source"] = "prospeo"
    for field in _PROSPEO_KNOWN_FIELDS:
        row.setdefault(field, None)
        row.setdefault(f"{field}_source", "prospeo")

    row["source_link"] = source_link
    return row
