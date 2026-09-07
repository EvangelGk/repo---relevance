"""Cross-checks datapoints that overlap by design and flags disagreement,
instead of leaving a human reviewer to eyeball every column for a mismatch.

Runs last (see import order in __init__.py) so every other extractor's
output is already in `context`:

- locale_conflict: site_locale_detect's detected language(s) vs
  pricing_locale_extract's currency imply incompatible markets (e.g. a
  JPY-only pricing page on a site detected as German with no Japanese or
  English) - EUR is deliberately treated as compatible with most European
  languages plus English, since an English-only site pricing in EUR is a
  normal European B2B SaaS pattern, not a data-quality issue.
- company_name_conflict: legal_entity_extract's footer legal name and an
  explicit company_name override disagree once legal suffixes
  (Inc/LLC/GmbH/...) are stripped - e.g. brand "Meta" vs legal "Meta
  Platforms, Inc." should flag; brand "Stripe" vs legal "Stripe, Inc."
  should not. (structured_data_extract used to be a third candidate here -
  removed 2026-09-08, since cleaned markdown never preserves the JSON-LD
  it needed.)
"""
import re

from ..base import DataPointExtractor, DataPointResult

_CURRENCY_LANGUAGE_HINTS = {
    "USD": {"en"},
    "GBP": {"en"},
    "JPY": {"ja"},
    "EUR": {"en", "de", "fr", "es", "it", "nl", "pt"},
}
_LEGAL_SUFFIX_RE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|gmbh|co|plc|s\.?a\.?|b\.?v\.?)\b\.?",
    re.IGNORECASE,
)


def _normalize_name(name):
    if not name:
        return None
    stripped = _LEGAL_SUFFIX_RE.sub("", name)
    stripped = re.sub(r"[^a-z0-9]+", "", stripped.lower())
    return stripped or None


class ConflictCheck(DataPointExtractor):
    name = "conflict_check"

    def extract(self, markdown: str, context: dict):
        locale_conflict, locale_detail = self._check_locale(context)
        name_conflict, name_detail = self._check_company_name(context)
        return DataPointResult(
            value=None,
            extra_columns={
                "locale_conflict": locale_conflict,
                "locale_conflict_detail": locale_detail,
                "company_name_conflict": name_conflict,
                "company_name_conflict_detail": name_detail,
            },
        )

    @staticmethod
    def _check_locale(context: dict):
        languages = context.get("site_locale_detect") or []
        currency = (context.get("pricing_locale_extract") or {}).get("currency_code")
        if not languages or not currency:
            return False, None
        expected = _CURRENCY_LANGUAGE_HINTS.get(currency)
        if not expected or (set(languages) & expected):
            return False, None
        return True, f"pricing page priced in {currency} but detected site language(s) {languages}"

    @staticmethod
    def _check_company_name(context: dict):
        candidates = {
            "legal_entity_extract": (context.get("legal_entity_extract") or {}).get("legal_name"),
            "context_override": context.get("company_name"),
        }
        named = {source: name for source, name in candidates.items() if name}
        distinct_normalized = {_normalize_name(name) for name in named.values()} - {None}
        if len(distinct_normalized) <= 1:
            return False, None
        detail = "; ".join(f"{source}={name!r}" for source, name in named.items())
        return True, detail
