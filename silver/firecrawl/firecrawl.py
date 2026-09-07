"""Firecrawl(): one call that runs every registered datapoint extractor
against a single cleaned-markdown input and returns one flat result -
ready to drop into a table as one column per datapoint, plus the raw
markdown for auditing.

The extractor list is never hardcoded here - it's read from base.REGISTRY,
which every DataPointExtractor subclass adds itself to on import. See
datapoints/__init__.py for the import order, which doubles as execution
order since later extractors read earlier ones' output out of `context`.

Firecrawl is pure execution: it runs every registered extractor against
whatever markdown it's given and reports what happened. It never decides
pass/fail or skips itself on relevance grounds - that gate
(is_company_profile) lives one layer up, in
silver_orchestrator.orchestrator.SilverOrchestrator, which is the thing
that decides whether to call Firecrawl at all for a given page.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import REGISTRY, DataPointExtractor, DataPointResult
from ._utils import extract_footer, extract_links

# The 17 datapoint functions whose emptiness/source get reported in
# run_all()'s function_report. Extractors outside this set are QA/cross-check
# passes (currently just conflict_check) that emit extra_columns rather than
# a datapoint of their own, so they're not part of the reported contract.
_QA_ONLY_EXTRACTORS = {"conflict_check"}


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple, set)) and len(value) == 0:
        return True
    return False


def _collapse_if_blank(value: Any) -> Any:
    """"Ran, found nothing" should read as a plain None, not a dict of all-
    null keys - so a reviewer scanning the table sees an obviously empty
    cell instead of a multi-key blob that looks like it might mean
    something."""
    if isinstance(value, dict) and all(_is_blank(v) for v in value.values()):
        return None
    return value


class Firecrawl:
    """One call -> every registered smaller function runs against the same
    markdown.

    Optional context overrides (fill in whatever the page can't supply on
    its own): source_url, source, company_name, parent_guess, entity_id,
    raw_date, current_year, detected_tools, timeseries_field,
    timeseries_value, snapshot_date, last_enriched_date,
    re_verification_due_date, regulatory_event_text / raw_event_text.
    """

    def __init__(self, extractors: Optional[List[DataPointExtractor]] = None):
        # Built lazily (not at class-definition time) so it reflects every
        # datapoint module __init__.py has imported by the time a
        # Firecrawl instance is actually created, not just at the moment
        # this module itself was first imported.
        self.extractors = extractors if extractors is not None else [cls() for cls in REGISTRY]

    def run_all(self, markdown: str, **context_overrides) -> dict:
        """Run every registered extractor against `markdown` and return
        {"row": {...}, "function_report": {...}}.

        `row` has one key per extractor (plus raw_markdown_input and
        run_timestamp) - the same flat shape run_all() always returned, and
        the only half run_all_as_dataframe() uses. `function_report` has one
        entry per one of the 17 datapoint functions -
        {"ran": bool, "is_empty": bool, "source": str | None} - for the
        orchestrator to score and gate on; it never appears in the CSV.
        """
        markdown = markdown or ""

        context: dict = dict(context_overrides)
        context["_links"] = extract_links(markdown)
        context["_footer_text"] = extract_footer(markdown)

        row: Dict[str, Any] = {
            "raw_markdown_input": markdown,
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        function_report: Dict[str, Dict[str, Any]] = {}

        for extractor in self.extractors:
            # Reset per call so a function that raises (and therefore never
            # reaches its own self._last_source assignment) doesn't leak a
            # stale value from a previous run_all() call on this instance.
            extractor._last_source = None

            ran = True
            try:
                outcome = extractor.extract(markdown, context)
            except Exception as exc:  # one bad extractor shouldn't sink the run
                outcome = {"error": f"{type(exc).__name__}: {exc}"}
                ran = False

            if isinstance(outcome, DataPointResult):
                value = _collapse_if_blank(outcome.value)
                row[extractor.name] = value
                context[extractor.name] = value
                if outcome.source is not None:
                    row[f"{extractor.name}_source"] = outcome.source
                for column, extra_value in outcome.extra_columns.items():
                    row[column] = extra_value
                    context[column] = extra_value
            else:
                value = _collapse_if_blank(outcome)
                row[extractor.name] = value
                context[extractor.name] = value

            if extractor.name not in _QA_ONLY_EXTRACTORS:
                function_report[extractor.name] = {
                    "ran": ran,
                    "is_empty": True if not ran else _is_blank(value),
                    "source": extractor._last_source,
                }

        return {"row": row, "function_report": function_report}

    def run_all_as_dataframe(self, markdown: str, **context_overrides) -> pd.DataFrame:
        """run_all()'s "row" half as a one-row DataFrame, with every
        non-scalar value JSON-encoded so it fits in a table cell - the shape
        the UI and the tests both want without duplicating the flattening
        logic. function_report is for the orchestrator, not the CSV, so it's
        dropped here."""
        row = self.run_all(markdown, **context_overrides)["row"]
        flat_row = {
            key: value if isinstance(value, (str, int, float, bool, type(None))) else json.dumps(value, default=str)
            for key, value in row.items()
        }
        return pd.DataFrame([flat_row])

    def run(self, markdown: str, **context_overrides) -> dict:
        """Kept for backward compatibility with existing callers - delegates
        to run_all()."""
        return self.run_all(markdown, **context_overrides)

    def run_batch(self, pages: List[Dict[str, Any]], max_workers: int = 8) -> List[dict]:
        """Run .run() over many pages at once.

        Each item in `pages` is a dict with a 'markdown' key plus whatever
        context overrides that page needs (source_url, entity_id, ...) -
        the same kwargs `run()` accepts. Returns one result dict per page,
        in the same order as `pages`. Uses a thread pool since each run()
        is independent, self-contained work with no shared state - except
        each self.extractors instance is shared across every worker thread,
        so a function's `_last_source` (and therefore function_report
        source) is not safe to rely on for a page processed concurrently
        with others through this method. SilverOrchestrator.process_batch
        avoids this by calling process_page() sequentially.
        """
        def _run_one(page: Dict[str, Any]) -> dict:
            page = dict(page)
            page_markdown = page.pop("markdown", "")
            return self.run(page_markdown, **page)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(_run_one, pages))
