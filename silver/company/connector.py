"""assemble_company_row(apify_company, firecrawl_row, source_link) -> dict

The `company/` connector: assembles one company row from two already-live
sources. `location`, `industry`, `headcount`, `linkedin_url` are still
single-source (Apify-only, no live Firecrawl candidate exists for any of
them) and stay pure static tagging. `name` is the one field with two real
live candidates - Apify's `name` and Firecrawl's
`company_entity_resolve.company_name` - so it's resolved via the foreman
(`silver/foreman/`, wired in 2026-09-08; see that package's README for why
it didn't exist here before).

Inputs:
  - `apify_company`: output of `apify/company/universal/extract.py`
    (`extract_company_universal_fields`) - a dict with `name`, `industry`,
    `headcount`, `location`, `linkedin_url` (all `_source: "apify"` except
    `name`, see above).
  - `firecrawl_row`: the `row` half of `Firecrawl.run_all()` (or
    `SilverOrchestrator.process_page()`, same row shape) - this connector
    reads `domain_normalize`, `company_entity_resolve`, and
    `company_description_extract` out of it directly rather than
    re-running or wrapping those extractors.
  - `source_link`: stamped from ingestion/batch context, not derived from
    any source folder - passed through as-is, no companion `_source` tag
    (it *is* the provenance value).
  - `dead_letter`/`drift`: optional, forwarded to
    `silver_orchestrator.orchestrator.evaluate_record` (same
    default-fresh-instance convention `SilverOrchestrator` itself uses) so
    callers/tests can scope where the Apify-side quality-gate state lands.

Output has one `<field>_source` per field except `company_id` and
`source_link` (see their docstring notes above for why), plus
`name_conflict` (True when Apify and Firecrawl genuinely disagreed on the
company name - see `foreman.priority_rules.PRIORITY_RULES["company_name"]`)
and `apify_quality_score`/`apify_is_valid_row`/`apify_rejection_reasons`/
`apify_drift_warnings` - the Apify half's own extraction quality, gated via
`silver_orchestrator.contracts.APIFY_COMPANY_CONTRACTS` independently of
the merge above (added 2026-09-08, part of scaling silver_orchestrator/
past Firecrawl-only).

**Behavior change (2026-09-08)**: when neither Apify nor Firecrawl has a
company name, `name_source` is now `None` instead of a hardcoded `"apify"`
- matches the "source is None when nothing was found" convention every
Firecrawl extractor already follows, now that `name` genuinely has a
resolution step that can report "no source won."
"""
from typing import Any, Dict, Optional

from silver.foreman.priority_rules import PRIORITY_RULES
from silver.foreman.source_priority_resolve import function_source_priority_resolve
from silver.silver_orchestrator.contracts import APIFY_COMPANY_CONTRACTS
from silver.silver_orchestrator.dead_letter import DeadLetterQueue
from silver.silver_orchestrator.drift import DriftTracker
from silver.silver_orchestrator.orchestrator import build_function_report, evaluate_record


def _resolve_name(apify_company: Dict[str, Any], firecrawl_row: Dict[str, Any]) -> Dict[str, Any]:
    entity = firecrawl_row.get("company_entity_resolve") or {}
    candidates = [
        {"source": "apify", "value": apify_company.get("name")},
        {"source": "firecrawl", "value": entity.get("company_name")},
    ]
    return function_source_priority_resolve(candidates, PRIORITY_RULES["company_name"])


def assemble_company_row(
    apify_company: Optional[Dict[str, Any]],
    firecrawl_row: Optional[Dict[str, Any]],
    source_link: Optional[str] = None,
    dead_letter: Optional[DeadLetterQueue] = None,
    drift: Optional[DriftTracker] = None,
) -> Dict[str, Any]:
    apify_company = apify_company or {}
    firecrawl_row = firecrawl_row or {}

    resolved_name = _resolve_name(apify_company, firecrawl_row)

    apify_gate = evaluate_record(
        apify_company,
        build_function_report(apify_company, source="apify"),
        APIFY_COMPANY_CONTRACTS,
        "apify_company",
        dead_letter=dead_letter,
        drift=drift,
    )

    return {
        "name": resolved_name["value"],
        "name_source": resolved_name["source"],
        "name_conflict": resolved_name["conflict"],
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
        "apify_quality_score": apify_gate["quality_score"],
        "apify_is_valid_row": apify_gate["is_valid_row"],
        "apify_rejection_reasons": apify_gate["rejection_reasons"],
        "apify_drift_warnings": apify_gate["drift_warnings"],
    }
