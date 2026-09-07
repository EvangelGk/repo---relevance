"""function_site_locale_detect(page language mentions) -> language_code: array

Another corroborating input for a location signal, and a data-quality
flag when it conflicts with claimed markets (see conflict_check.py, which
cross-checks this against pricing_locale_extract's currency).

HTML-attribute detection (<html lang>, <link hreflang>) was removed
2026-09-08: cleaned markdown never preserves those attributes, so that
path was structurally dead against real input - it only ever fired on a
raw-HTML test fixture, never on a genuine Firecrawl scrape. What's left is
the part that actually works on markdown text: a canonical
language-name-to-code table plus a scan for parenthetical 2-letter codes
(e.g. "English (EN)"), returned in the order they first appear on the page.
"""
import re

from ..base import DataPointExtractor

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
        self._last_source = "markdown" if ordered_codes else None
        return ordered_codes
