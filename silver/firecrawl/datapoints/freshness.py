"""function_freshness(last enriched date, re-verification due date) ->
{is_stale: bool, days_since_enriched: int}

Needs `last_enriched_date` (and optionally `re_verification_due_date`) in
context - these describe the enrichment record's lifecycle, not something
derivable from the page itself.
"""
from datetime import date, datetime

from ..base import DataPointExtractor


class Freshness(DataPointExtractor):
    name = "freshness"

    def extract(self, markdown: str, context: dict):
        last_enriched = context.get("last_enriched_date")
        if not last_enriched:
            self._last_source = None
            return None

        last_enriched_dt = self._parse(last_enriched)
        today = date.today()
        days_since = (today - last_enriched_dt).days if last_enriched_dt else None

        due = context.get("re_verification_due_date")
        is_stale = False
        if due:
            due_dt = self._parse(due)
            is_stale = bool(due_dt and today >= due_dt)

        self._last_source = "context"
        return {"is_stale": is_stale, "days_since_enriched": days_since}

    @staticmethod
    def _parse(value):
        if isinstance(value, date):
            return value
        try:
            return datetime.fromisoformat(str(value)).date()
        except ValueError:
            return None
