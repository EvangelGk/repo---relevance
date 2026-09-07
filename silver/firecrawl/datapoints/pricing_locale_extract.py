"""function_pricing_locale_extract(pricing-page raw text - currency
symbols, plan tiers, often malformed as markdown tables) ->
{currency_code, price_points, billing_model_hint}

Corroborates or contradicts self-reported revenue model and locations
served - a EUR-only pricing page is a stronger locations signal than the
"About" page's claims. conflict_check.py cross-checks currency_code
against site_locale_detect's detected language(s).
"""
import re

from ..base import DataPointExtractor
from .._utils import PRICE_RE, find_section

_SYMBOL_TO_CODE = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_BILLING_HINTS = {
    "FREEMIUM": r"\bfree (?:plan|forever|tier)\b|freemium",
    "USAGE": r"per (?:seat|user|api call|request|credit|unit)|usage[- ]based|pay as you go",
    "PERPETUAL": r"one[- ]time (?:payment|fee)|lifetime license|perpetual license",
    "SUBSCRIPTION": r"/\s?(?:mo|month|year|yr)\b|monthly|annually|per month|per year",
}


class PricingLocaleExtract(DataPointExtractor):
    name = "pricing_locale_extract"

    def extract(self, markdown: str, context: dict):
        section = find_section(markdown, ["pricing", "plans"]) or markdown
        price_points = PRICE_RE.findall(section)
        if not price_points:
            self._last_source = None
            return None

        currency_code = None
        for token in price_points:
            symbol = token[0]
            currency_code = _SYMBOL_TO_CODE.get(symbol)
            if currency_code:
                break
            letters = re.match(r"[A-Z]{3}", token)
            if letters:
                currency_code = letters.group(0)
                break

        billing_model_hint = next(
            (label for label, pattern in _BILLING_HINTS.items() if re.search(pattern, section, re.IGNORECASE)),
            None,
        )
        self._last_source = "markdown"
        return {
            "currency_code": currency_code,
            "price_points": price_points[:20],
            "billing_model_hint": billing_model_hint,
        }
