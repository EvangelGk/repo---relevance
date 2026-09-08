"""function_topic_classify(text: str | list[str]) -> list[str]

Case-insensitive, word-boundary alias matching against a fixed topic
taxonomy - the same pattern Firecrawl's `compliance_framework_extract`
uses, applied here to a person's bio/about text or post captions instead
of company-website markdown. An empty list is the correct, expected
answer when nothing in the taxonomy is mentioned - not a sign of failure.

Accepts either a single text blob or a list of text snippets (e.g. one
per post) - a list is joined before matching.
"""
import re
from typing import List, Union

_ALIASES = {
    "AI_ML": ["artificial intelligence", "machine learning", "generative ai", "llm", "deep learning"],
    "SAAS": ["saas", "software as a service"],
    "FINTECH": ["fintech", "financial technology", "payments"],
    "HEALTHTECH": ["healthtech", "digital health", "healthcare technology"],
    "CYBERSECURITY": ["cybersecurity", "infosec", "information security"],
    "SALES": ["sales", "revenue growth", "go-to-market", "gtm"],
    "MARKETING": ["marketing", "growth marketing", "demand generation"],
    "RECRUITING": ["recruiting", "talent acquisition", "hiring"],
    "VENTURE_CAPITAL": ["venture capital", "vc", "startup investing"],
    "CLIMATE": ["climate tech", "sustainability", "clean energy"],
}


def _build_patterns():
    compiled = {}
    for topic, aliases in _ALIASES.items():
        alternatives = [re.escape(alias).replace(r"\ ", r"\s+") for alias in aliases]
        compiled[topic] = re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)
    return compiled


_PATTERNS = _build_patterns()


def function_topic_classify(text: Union[str, List[str], None]) -> List[str]:
    if text is None:
        return []
    blob = text if isinstance(text, str) else "\n".join(t for t in text if t)
    return [topic for topic, pattern in _PATTERNS.items() if pattern.search(blob)]
