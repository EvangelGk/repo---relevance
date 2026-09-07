"""function_company_entity_resolve(domain [Firecrawl], company name,
parent_guess) -> company_id: canonical key

Reads domain_normalize and legal_entity_extract's output out of context
rather than re-deriving them, so the three inputs agree on the same page.
When context["parent_guess"] isn't given, scans the markdown for plain-
prose parent-company language ("is a subsidiary of X", "part of X") so a
stated relationship isn't silently dropped just because no one filled in
the override. An explicit context["parent_guess"] always wins over a
markdown-scanned guess; the result is tagged with "source": "context" or
"markdown" (None when no parent_guess was found either way).
"""
import re

from ..base import DataPointExtractor

_PARENT_PATTERNS = [
    re.compile(r"is a subsidiary of ([A-Z][\w&.,\- ]+)"),
    re.compile(r"a (?:wholly[- ]owned )?subsidiary of ([A-Z][\w&.,\- ]+)"),
    re.compile(r"part of ([A-Z][\w&.,\- ]+)"),
]


class CompanyEntityResolve(DataPointExtractor):
    name = "company_entity_resolve"

    def extract(self, markdown: str, context: dict):
        domain = context.get("domain_normalize")
        legal = context.get("legal_entity_extract") or {}
        company_name = context.get("company_name") or legal.get("legal_name")

        parent_guess = context.get("parent_guess")
        source = "context" if parent_guess else None
        if not parent_guess:
            parent_guess, source = self._scan_parent_guess(markdown)

        if not domain and not company_name:
            self._last_source = None
            return None

        key_source = parent_guess or domain or company_name
        self._last_source = source
        return {
            "company_id": self._slugify(key_source),
            "domain": domain,
            "company_name": company_name,
            "parent_guess": parent_guess,
            "source": source,
        }

    @staticmethod
    def _scan_parent_guess(markdown: str):
        for pattern in _PARENT_PATTERNS:
            match = pattern.search(markdown)
            if not match:
                continue
            candidate = re.split(r"[.!?;\n]", match.group(1), maxsplit=1)[0]
            candidate = candidate.strip().rstrip(",")
            if candidate:
                return candidate, "markdown"
        return None, None

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
        return slug.strip("-")
