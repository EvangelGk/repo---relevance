"""assemble_company_row(apify_company, firecrawl_row, source_link) -> dict

The `company/` connector: assembles one company row from two already-live
sources, with no reconciliation step in the middle. Every company field is
single-source: `location` turned out to be Apify-only (no live Firecrawl
candidate exists), and `founded_year` reconciliation (LinkedIn/Firecrawl/
CrunchBase via the foreman) was dropped from this repo entirely - no
foreman exists, and a reconcile target with only one real candidate isn't
useful. So this connector is pure static tagging, not a merge.

Inputs:
  - `apify_company`: output of `apify/company/universal/extract.py`
    (`extract_company_universal_fields`) - a dict with `name`, `industry`,
    `headcount`, `location`, `linkedin_url` (all `_source: "apify"`).
  - `firecrawl_row`: the `row` half of `Firecrawl.run_all()` (or
    `SilverOrchestrator.process_page()`, same row shape) - this connector
    reads `domain_normalize`, `company_entity_resolve`, and
    `company_description_extract` out of it directly rather than
    re-running or wrapping those extractors.
  - `source_link`: stamped from ingestion/batch context, not derived from
    any source folder - passed through as-is, no companion `_source` tag
    (it *is* the provenance value).

Output has one `<field>_source` per field except `company_id` and
`source_link` (see their docstring notes above for why).
"""
from typing import Any, Dict, Optional


def assemble_company_row(
    apify_company: Optional[Dict[str, Any]],
    firecrawl_row: Optional[Dict[str, Any]],
    source_link: Optional[str] = None,
) -> Dict[str, Any]:
    apify_company = apify_company or {}
    firecrawl_row = firecrawl_row or {}

    return {
        "name": apify_company.get("name"),
        "name_source": "apify",
        "industry": apify_company.get("industry"),
        "industry_source": "apify",
        "headcount": apify_company.get("headcount"),
        "headcount_source": "apify",
        "location": apify_company.get("location"),
        "location_source": "apify",
        "linkedin_url": apify_company.get("linkedin_url"),
        "linkedin_url_source": "apify",
        "domain": firecrawl_row.get("domain_normalize"),
        "domain_source": "firecrawl",
        "description": firecrawl_row.get("company_description_extract"),
        "description_source": "firecrawl",
        "company_id": firecrawl_row.get("company_entity_resolve"),
        "source_link": source_link,
    }
