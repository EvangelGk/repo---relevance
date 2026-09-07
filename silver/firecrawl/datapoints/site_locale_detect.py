"""function_site_locale_detect(page language / hreflang tags) ->
language_code: array

Another corroborating input for a location signal, and a data-quality
flag when it conflicts with claimed markets (see conflict_check.py, which
cross-checks this against pricing_locale_extract's currency). Cleaned
markdown usually drops <html lang> / <link hreflang>, so this falls back
to a canonical language-name-to-code table plus a scan for parenthetical
2-letter codes (e.g. "English (EN)"), returned in the order they first
appear on the page.
"""
import re

from ..base import DataPointExtractor
from .._utils import HREFLANG_RE, LANG_ATTR_RE

_LANGUAGE_NAMES = {
    "english": "en",
    "deutsch": "de",
    "german": "de",
    "français": "fr",
    "francais": "fr",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
    "portuguese": "pt",
    "dutch": "nl",
    "polish": "pl",
    "turkish": "tr",
    "russian": "ru",
    "japanese": "ja",
    "chinese": "zh",
    "korean": "ko",
    "arabic": "ar",
}
_KNOWN_CODES = set(_LANGUAGE_NAMES.values())
_NAME_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in _LANGUAGE_NAMES) + r")\b", re.IGNORECASE
)
_PAREN_CODE_RE = re.compile(r"\(([A-Za-z]{2})\)")


class SiteLocaleDetect(DataPointExtractor):
    name = "site_locale_detect"

    def extract(self, markdown: str, context: dict):
        tags = {m.lower() for m in LANG_ATTR_RE.findall(markdown)}
        tags |= {m.lower() for m in HREFLANG_RE.findall(markdown)}
        if tags:
            self._last_source = "hreflang"
            return sorted(tags)

        hits = [(m.start(), _LANGUAGE_NAMES[m.group(1).lower()]) for m in _NAME_RE.finditer(markdown)]
        for m in _PAREN_CODE_RE.finditer(markdown):
            code = m.group(1).lower()
            if code in _KNOWN_CODES:
                hits.append((m.start(), code))

        hits.sort(key=lambda pair: pair[0])
        seen = set()
        ordered_codes = []
        for _, code in hits:
            if code not in seen:
                seen.add(code)
                ordered_codes.append(code)
        self._last_source = "markdown_fallback" if ordered_codes else None
        return ordered_codes
