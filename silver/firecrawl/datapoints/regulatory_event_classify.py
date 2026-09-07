"""function_regulatory_event_classify(raw regulatory event type text, new
source) -> enum{RECALL, APPROVAL, WARNING_LETTER, LICENSE_GRANTED,
LICENSE_REVOKED, OTHER}

Normalizes the event *type* the way date_normalize normalizes the event
*date*, so trigger logic can branch on a controlled string instead of an
uncontrolled one. Prefers an explicit context override
(regulatory_event_text, or raw_event_text) but - like tech_stack_normalize
and company_entity_resolve - falls back to scanning the markdown itself
rather than staying dark whenever no override was supplied. Reports which
one it used as `regulatory_event_classify_source` ("context" | "markdown").
"""
import re

from ..base import DataPointExtractor, DataPointResult

# Richer rules for classifying an explicit, already-isolated event-type string.
_CONTEXT_RULES = {
    "RECALL": [r"\brecall(?:ed)?\b", r"\bwithdrawal of (?:product|device)\b"],
    "APPROVAL": [r"\bapprov(?:ed|al)\b", r"\bclear(?:ed|ance)\b", r"\bauthoriz(?:ed|ation)\b"],
    "WARNING_LETTER": [r"\bwarning letter\b", r"\buntitled letter\b"],
    "LICENSE_GRANTED": [r"\blicen[cs]e (?:granted|issued)\b", r"\bnew licen[cs]e\b"],
    "LICENSE_REVOKED": [r"\blicen[cs]e (?:revoked|suspended|terminated)\b"],
}
# Narrower literal keywords for scanning a whole page of prose.
_MARKDOWN_RULES = {
    "RECALL": [r"\brecall\b"],
    "WARNING_LETTER": [r"\bwarning letter\b"],
    "APPROVAL": [r"\bapproval\b", r"\bapproved\b"],
    "LICENSE_GRANTED": [r"\blicen[cs]e granted\b"],
    "LICENSE_REVOKED": [r"\blicen[cs]e revoked\b"],
}
_REGULATORY_HINT_RE = re.compile(
    r"\b(regulat\w*|compliance|FDA|EMA|regulator|authority|agency|certif\w*)\b", re.IGNORECASE
)


class RegulatoryEventClassify(DataPointExtractor):
    name = "regulatory_event_classify"

    def extract(self, markdown: str, context: dict):
        text = context.get("regulatory_event_text") or context.get("raw_event_text")
        if text:
            label = self._match(text, _CONTEXT_RULES) or "OTHER"
            self._last_source = "context"
            return DataPointResult(value=label, source="context")

        label = self._match(markdown, _MARKDOWN_RULES)
        if label:
            self._last_source = "markdown"
            return DataPointResult(value=label, source="markdown")
        if _REGULATORY_HINT_RE.search(markdown):
            self._last_source = "markdown"
            return DataPointResult(value="OTHER", source="markdown")
        self._last_source = None
        return None

    @staticmethod
    def _match(text: str, rules: dict):
        lowered = text.lower()
        for label, patterns in rules.items():
            if any(re.search(p, lowered) for p in patterns):
                return label
        return None
