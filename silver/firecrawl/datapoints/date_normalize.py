"""function_date_normalize(any raw date string [Apify or Firecrawl]) ->
list of ISO-8601 dates

Scans the whole page for date-shaped substrings (ISO, slash, and
month-name formats), parses each candidate with dateutil, and returns the
deduped ISO-8601 dates found - a company's own page routinely mentions
several dates (founding, copyright, latest funding round, blog post) and
picking just the first one throws information away. When
context["raw_date"] is given it is parsed too and placed first in the
list as the primary date. Reports whether an override contributed as
`date_normalize_source` ("context_override" | "markdown_scan").
"""
import re
from datetime import datetime

from ..base import DataPointExtractor, DataPointResult

try:
    from dateutil import parser as _dateutil_parser
except ImportError:  # pragma: no cover - optional dependency
    _dateutil_parser = None

_CANDIDATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2}?,?\s*\d{4}\b"
    ),
]


class DateNormalize(DataPointExtractor):
    name = "date_normalize"

    def extract(self, markdown: str, context: dict):
        results = []
        seen = set()
        source = None

        raw_date = context.get("raw_date")
        if raw_date:
            parsed = self.normalize(raw_date)
            if parsed and parsed not in seen:
                results.append(parsed)
                seen.add(parsed)
                source = "context_override"

        for pattern in _CANDIDATE_PATTERNS:
            for candidate in pattern.findall(markdown):
                parsed = self.normalize(candidate)
                if parsed and parsed not in seen:
                    results.append(parsed)
                    seen.add(parsed)
                    if source is None:
                        source = "markdown_scan"

        if not results:
            self._last_source = None
            return None
        self._last_source = "markdown"
        return DataPointResult(value=results, source=source)

    @staticmethod
    def normalize(raw_date):
        if not raw_date:
            return None
        if _dateutil_parser is not None:
            try:
                return _dateutil_parser.parse(str(raw_date), fuzzy=True).date().isoformat()
            except (ValueError, OverflowError, TypeError):
                return None
        try:
            return datetime.fromisoformat(str(raw_date)).date().isoformat()
        except ValueError:
            return None
