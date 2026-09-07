"""function_tech_stack_normalize(detected tool names [website scrape]) ->
{detected_stack, mentioned_technologies}

detected_stack is populated ONLY from context["detected_tools"] (a real
website-fingerprinting input, e.g. from a tag-manager/script scan) -
never from markdown - and is deduped, alias-collapsed, and categorized
(CRM/analytics/support/...). mentioned_technologies is a separate,
markdown-only scan for vendor/product names mentioned in prose.

mentioned_technologies reflects what a company talks about (competencies,
integrations, partners) - it is NOT evidence of what they actually run.
Do not treat it as equivalent to detected_stack in any downstream scoring.
"""
import re

from ..base import DataPointExtractor

_CATALOG = {
    "salesforce": {"category": "CRM", "aliases": ["salesforce"]},
    "hubspot": {"category": "CRM", "aliases": ["hubspot"]},
    "google_analytics": {"category": "ANALYTICS", "aliases": ["google analytics", "gtag", "googletagmanager"]},
    "segment": {"category": "ANALYTICS", "aliases": ["segment"]},
    "mixpanel": {"category": "ANALYTICS", "aliases": ["mixpanel"]},
    "amplitude": {"category": "ANALYTICS", "aliases": ["amplitude"]},
    "intercom": {"category": "SUPPORT", "aliases": ["intercom"]},
    "zendesk": {"category": "SUPPORT", "aliases": ["zendesk"]},
    "drift": {"category": "SUPPORT", "aliases": ["drift"]},
    "stripe": {"category": "PAYMENTS", "aliases": ["stripe"]},
    "shopify": {"category": "ECOMMERCE", "aliases": ["shopify"]},
    "marketo": {"category": "MARKETING", "aliases": ["marketo"]},
    "mailchimp": {"category": "MARKETING", "aliases": ["mailchimp"]},
    "klaviyo": {"category": "MARKETING", "aliases": ["klaviyo"]},
    "pardot": {"category": "MARKETING", "aliases": ["pardot"]},
    "wordpress": {"category": "CMS", "aliases": ["wordpress", "wp-content"]},
    "webflow": {"category": "CMS", "aliases": ["webflow"]},
    "cloudflare": {"category": "INFRA", "aliases": ["cloudflare"]},
}
_PATTERNS = {
    tool_id: re.compile(r"\b(?:" + "|".join(re.escape(a) for a in entry["aliases"]) + r")\b", re.IGNORECASE)
    for tool_id, entry in _CATALOG.items()
}


def _resolve(raw_name: str):
    for tool_id, pattern in _PATTERNS.items():
        if pattern.search(raw_name):
            return tool_id, _CATALOG[tool_id]["category"]
    return None


class TechStackNormalize(DataPointExtractor):
    name = "tech_stack_normalize"

    def extract(self, markdown: str, context: dict):
        mentioned = [
            {"tool_id": tool_id, "category": _CATALOG[tool_id]["category"]}
            for tool_id, pattern in _PATTERNS.items()
            if pattern.search(markdown)
        ]

        detected_stack = []
        seen_ids = set()
        for raw_name in context.get("detected_tools") or []:
            resolved = _resolve(str(raw_name))
            if resolved:
                tool_id, category = resolved
            else:
                tool_id = re.sub(r"[^a-z0-9]+", "_", str(raw_name).strip().lower()).strip("_")
                category = None
            if tool_id and tool_id not in seen_ids:
                seen_ids.add(tool_id)
                detected_stack.append({"tool_id": tool_id, "category": category})

        if detected_stack:
            self._last_source = "context"
        elif mentioned:
            self._last_source = "markdown"
        else:
            self._last_source = None
        return {"detected_stack": detected_stack, "mentioned_technologies": mentioned}
