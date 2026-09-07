"""function_experience_signal_extract(markdown, optional
context["current_year"]) -> {founding_year, founding_year_source,
years_in_business_claim}

Kept separate from date_normalize - that one normalizes calendar dates
that already appear in a specific format; this one reads duration and
founding *claims* out of marketing prose ("Founded in 2015", "over 30
years of experience") and, when only a duration is given, derives a
founding year from it.
"""
import re
from datetime import datetime, timezone

from ..base import DataPointExtractor

_EXPLICIT_PATTERNS = [
    r"[Ff]ounded in (\d{4})",
    r"[Ee]stablished in (\d{4})",
    r"[Ss]ince (\d{4})",
]
_DURATION_PATTERNS = [
    r"(?:over|more than)\s+(\d+)\s+years",
    r"(\d+)\+?\s+years?\s+(?:of experience|combined experience|in the industry)",
]


class ExperienceSignalExtract(DataPointExtractor):
    name = "experience_signal_extract"

    def extract(self, markdown: str, context: dict):
        current_year = context.get("current_year") or datetime.now(timezone.utc).year

        explicit_year = None
        for pattern in _EXPLICIT_PATTERNS:
            match = re.search(pattern, markdown)
            if match:
                explicit_year = int(match.group(1))
                break

        duration_claim = None
        for pattern in _DURATION_PATTERNS:
            match = re.search(pattern, markdown)
            if match:
                duration_claim = int(match.group(1))
                break

        if explicit_year is not None:
            self._last_source = "markdown"
            return {
                "founding_year": explicit_year,
                "founding_year_source": "explicit",
                "years_in_business_claim": duration_claim,
            }
        if duration_claim is not None:
            self._last_source = "markdown"
            return {
                "founding_year": current_year - duration_claim,
                "founding_year_source": "derived",
                "years_in_business_claim": duration_claim,
            }
        self._last_source = None
        return {
            "founding_year": None,
            "founding_year_source": None,
            "years_in_business_claim": None,
        }
