"""function_legal_entity_extract(footer copyright text, e.g. "© 2024
Acme Inc.") -> {legal_name, copyright_year}

Gives the registrable legal name vs. the marketing brand name - two
different strings for the same company, and a real entity-resolution
trap. conflict_check.py cross-checks this against an explicit
company_name context override, if one was given.
"""
import re

from ..base import DataPointExtractor
from .._utils import extract_footer

_COPYRIGHT_RE = re.compile(
    r"©\s*(?P<year>\d{4})?\s*,?\s*(?P<name>[A-Z][\w&.,'’\-\s]{1,80}?)"
    r"(?=\s*\.?(?:\s+All rights reserved|\s*[|\n]|\s*$))",
)


class LegalEntityExtract(DataPointExtractor):
    name = "legal_entity_extract"

    def extract(self, markdown: str, context: dict):
        footer = context.get("_footer_text") or extract_footer(markdown)
        match = _COPYRIGHT_RE.search(footer) or _COPYRIGHT_RE.search(markdown)
        if not match:
            self._last_source = None
            return None
        name = match.group("name").strip().strip(".,")
        if not name:
            self._last_source = None
            return None
        year = match.group("year")
        self._last_source = "markdown"
        return {
            "legal_name": name,
            "copyright_year": int(year) if year else None,
        }
