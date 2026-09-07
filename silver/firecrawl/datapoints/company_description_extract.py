"""function_company_description_extract(page prose, optional context
override) -> company_description: str

A short, human-readable summary of what the company does - the kind of
line a reader would use to explain the company in one sentence. Prefers an
explicit context["company_description"] override (e.g. a scraped meta
description or an Apify-supplied summary) over a markdown guess, since a
hand-authored description is more reliable than heuristically picking "the
first real paragraph." Falls back to the first substantive prose paragraph
on the page - skipping headings and short nav/breadcrumb-shaped lines -
when no override is given.
"""
import re

from ..base import DataPointExtractor

_MIN_WORDS = 6
_MAX_LENGTH = 500


class CompanyDescriptionExtract(DataPointExtractor):
    name = "company_description_extract"

    def extract(self, markdown: str, context: dict):
        override = context.get("company_description")
        if override and str(override).strip():
            self._last_source = "context"
            return str(override).strip()[:_MAX_LENGTH]

        for paragraph in re.split(r"\n\s*\n", markdown or ""):
            stripped = paragraph.strip()
            if not stripped or stripped.startswith("#"):
                continue
            candidate = re.sub(r"[*_`]", "", stripped)
            candidate = re.sub(r"^\s*[-*]\s*", "", candidate)
            candidate = re.sub(r"\s+", " ", candidate).strip()
            if len(candidate.split()) >= _MIN_WORDS:
                self._last_source = "markdown"
                return candidate[:_MAX_LENGTH]

        self._last_source = None
        return None
