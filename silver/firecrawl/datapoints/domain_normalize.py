"""function_domain_normalize(raw URL, source) -> root_domain

The actual join key across Firecrawl + LinkedIn + Crunchbase + G2. Strips
protocol, www, and tracking subdomains (app./docs./blog./marketing.) plus
query/UTM params, so a marketing site vs. app. vs docs. subdomain don't
resolve to three different "companies" - the single most common
entity-resolution bug in this pipeline.
"""
from urllib.parse import urlparse

from ..base import DataPointExtractor

_TRACKING_SUBDOMAINS = {
    "www", "app", "docs", "blog", "marketing", "get", "go", "try",
    "shop", "store", "help", "support", "status", "mail",
}


class DomainNormalize(DataPointExtractor):
    name = "domain_normalize"

    def extract(self, markdown: str, context: dict):
        raw_url = context.get("source_url")
        source = context.get("source", "firecrawl")
        used_context_override = bool(raw_url)
        if not raw_url:
            links = context.get("_links") or []
            raw_url = next((url for _, url in links), None)
        if not raw_url:
            self._last_source = None
            return None
        value = self.normalize(raw_url, source)
        self._last_source = ("context" if used_context_override else "markdown") if value else None
        return value

    @staticmethod
    def normalize(raw_url: str, source: str = "firecrawl"):
        if not raw_url:
            return None
        candidate = raw_url if "://" in raw_url else f"https://{raw_url}"
        try:
            host = urlparse(candidate).netloc.lower()
        except ValueError:
            return None
        host = host.split("@")[-1].split(":")[0]
        if not host:
            return None
        labels = host.split(".")
        while len(labels) > 2 and labels[0] in _TRACKING_SUBDOMAINS:
            labels = labels[1:]
        return ".".join(labels) or None
