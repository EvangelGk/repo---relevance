"""function_business_model(revenue model, offering type, delivery model,
internal structure [website]) ->
{pricing: {primary, secondary|None}, offering: {primary, secondary|None},
delivery: {primary, secondary|None}}

Reuses pricing_locale_extract's billing_model_hint when available (a
pricing-page signal outranks a homepage-copy guess) and otherwise scores
keyword hits per candidate rather than returning whichever pattern
happened to be checked first - a page mentioning both subscription and
usage-based language gets pricing={"primary": "SUBSCRIPTION",
"secondary": "USAGE"} instead of silently picking one. Delivery is a
special case: when both self-serve and sales-led language fire, the
honest answer is "HYBRID", not a coin flip between the two.
"""
import re

from ..base import DataPointExtractor

_PRICING_PATTERNS = {
    "FREEMIUM": [r"\bfree (?:plan|forever|tier)\b", r"freemium"],
    "USAGE": [r"pay as you go", r"usage[- ]based", r"per (?:seat|api call|credit)"],
    "PERPETUAL": [r"one[- ]time payment", r"perpetual license"],
    "SUBSCRIPTION": [r"/\s?(?:mo|month|year)\b", r"subscription"],
}
_OFFERING_PATTERNS = {
    "MARKETPLACE": [r"\bmarketplace\b", r"buyers and sellers"],
    "HARDWARE": [r"\bhardware\b", r"\bdevices?\b", r"ships? to your"],
    "DATA": [r"\bdatasets?\b", r"\bapi (?:access|credits)\b", r"data provider"],
    "SERVICES": [r"\bconsulting\b", r"\bmanaged service\b", r"\bprofessional services\b"],
    "SAAS": [r"\bsaas\b", r"\bsoftware\b", r"\bplatform\b", r"\bcloud[- ]based\b"],
}
_SELF_SERVE_PATTERNS = [r"\bsign up free\b", r"\bstart free trial\b", r"\bself[- ]serve\b"]
_SALES_LED_PATTERNS = [r"\bcontact sales\b", r"\bbook a demo\b", r"\btalk to sales\b", r"\brequest a demo\b"]


class BusinessModel(DataPointExtractor):
    name = "business_model"

    def extract(self, markdown: str, context: dict):
        text = markdown.lower()

        pricing_hint = (context.get("pricing_locale_extract") or {}).get("billing_model_hint")
        pricing = {"primary": pricing_hint, "secondary": None} if pricing_hint else self._scored_pick(text, _PRICING_PATTERNS)

        offering = self._scored_pick(text, _OFFERING_PATTERNS)
        delivery = self._score_delivery(text)

        any_value = any(d["primary"] is not None for d in (pricing, offering, delivery))
        if pricing_hint:
            self._last_source = "context"
        elif any_value:
            self._last_source = "markdown"
        else:
            self._last_source = None

        return {"pricing": pricing, "offering": offering, "delivery": delivery}

    @staticmethod
    def _scored_pick(text: str, patterns: dict):
        scores = {
            label: sum(len(re.findall(p, text)) for p in regexes)
            for label, regexes in patterns.items()
        }
        ranked = sorted((item for item in scores.items() if item[1] > 0), key=lambda item: item[1], reverse=True)
        if not ranked:
            return {"primary": None, "secondary": None}
        primary_label, primary_score = ranked[0]
        secondary_label = None
        if len(ranked) > 1 and (primary_score - ranked[1][1]) <= 1:
            secondary_label = ranked[1][0]
        return {"primary": primary_label, "secondary": secondary_label}

    @staticmethod
    def _score_delivery(text: str):
        self_serve_hits = sum(len(re.findall(p, text)) for p in _SELF_SERVE_PATTERNS)
        sales_led_hits = sum(len(re.findall(p, text)) for p in _SALES_LED_PATTERNS)
        if self_serve_hits and sales_led_hits:
            return {"primary": "HYBRID", "secondary": None}
        if self_serve_hits:
            return {"primary": "SELF_SERVE", "secondary": None}
        if sales_led_hits:
            return {"primary": "SALES_LED", "secondary": None}
        return {"primary": None, "secondary": None}
