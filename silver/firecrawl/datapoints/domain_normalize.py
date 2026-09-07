"""function_domain_normalize(raw URL, source) -> root_domain

The actual join key across Firecrawl + LinkedIn + Crunchbase + G2. Strips
protocol, www, and tracking subdomains (app./docs./blog./marketing.) plus
query/UTM params, so a marketing site vs. app. vs docs. subdomain don't
resolve to three different "companies" - the single most common
entity-resolution bug in this pipeline.

context["source_url"]-only (fixed 2026-09-08). This used to fall back to
"the first link found anywhere on the page" when no source_url was given -
but that guess is frequently *wrong*, not just empty: a footer's first
link is often a social profile (LinkedIn, Twitter) or a partner site, not
the page's own domain, so the fallback could confidently mislabel a row
under someone else's domain. Scraping a page always requires already
knowing its URL, so context["source_url"] should be supplied by whatever
pipeline calls Firecrawl - this function no longer guesses when it isn't.
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
        if not raw_url:
            self._last_source = None
            return None
        value = self.normalize(raw_url, source)
        self._last_source = "context" if value else None
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
