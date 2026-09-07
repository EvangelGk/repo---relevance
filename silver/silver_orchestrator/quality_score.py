"""Turns a Firecrawl function_report into one 0-100 quality score for a row.

Two penalties, both additive off a 100.0 baseline:
- A required-but-empty function (domain_normalize, company_entity_resolve)
  is a join-key failure, not a soft miss - it costs 30 points, heavy enough
  that a single missing join key visibly tanks the score.
- Any function that ran but used a source ranked below the best available
  one in its contract's source_priority (e.g. site_locale_detect falling
  back to "markdown_fallback" instead of "hreflang") costs 2 points per
  occurrence - a much softer signal, since a lower-confidence source still
  produced a usable value.
"""
from typing import Dict

from .contracts import DatapointContract

_REQUIRED_EMPTY_PENALTY = 30.0
_LOW_PRIORITY_SOURCE_PENALTY = 2.0


def compute_quality_score(function_report: Dict[str, dict], contracts: Dict[str, DatapointContract]) -> float:
    score = 100.0

    for name, contract in contracts.items():
        entry = function_report.get(name)
        if entry is None:
            continue

        if contract.required and entry.get("is_empty"):
            score -= _REQUIRED_EMPTY_PENALTY

        source = entry.get("source")
        if source is not None and contract.source_priority and source in contract.source_priority:
            if contract.source_priority.index(source) > 0:
                score -= _LOW_PRIORITY_SOURCE_PENALTY

    return max(0.0, min(100.0, score))
