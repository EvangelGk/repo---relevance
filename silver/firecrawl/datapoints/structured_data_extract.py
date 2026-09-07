"""function_structured_data_extract(schema.org JSON-LD, when the page has it)
-> {name, address, sameAs, aggregateRating, numberOfEmployees, foundingDate}

When present this is higher-confidence than anything parsed from markdown
prose elsewhere in this pipeline and should outrank free-text extraction,
not just supplement it. `name` is kept alongside the rest specifically so
conflict_check.py can cross-check the JSON-LD brand name against
legal_entity_extract's footer legal name.
"""
from ..base import DataPointExtractor
from .._utils import extract_json_ld


class StructuredDataExtract(DataPointExtractor):
    name = "structured_data_extract"

    def extract(self, markdown: str, context: dict):
        # This codebase has no separate context["raw_html"] channel - JSON-LD
        # is parsed straight out of whatever raw <script> markup survived
        # into `markdown` (see tests/sample_input.html). "html" here means
        # "a <script type=application/ld+json> block was found and parsed",
        # which is the closest equivalent to that context key's intent.
        blocks = extract_json_ld(markdown)
        if not blocks:
            self._last_source = None
            return None
        org = next(
            (b for b in blocks if str(b.get("@type", "")).lower() in ("organization", "corporation")),
            blocks[0],
        )
        same_as = org.get("sameAs")
        if isinstance(same_as, str):
            same_as = [same_as]
        self._last_source = "html"
        return {
            "name": org.get("name"),
            "address": org.get("address"),
            "sameAs": same_as or [],
            "aggregateRating": org.get("aggregateRating"),
            "numberOfEmployees": org.get("numberOfEmployees"),
            "foundingDate": org.get("foundingDate"),
        }
