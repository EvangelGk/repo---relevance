"""function_social_links_extract(raw footer/nav links) ->
{linkedin_url, twitter_url, crunchbase_url, g2_url, capterra_url, youtube_url}

Auto-discovers what a manual process assumed was a hand-cited "G2 profile
url" - instead of requiring that as a separate enrichment step. Runs its
own regex pass directly over markdown (markdown-link syntax first) and
falls back to a bare-URL scan only when that pass finds nothing, so a URL
still gets classified if link brackets were stripped before this function
saw the text but the raw URL text survived.
"""
import re

from ..base import DataPointExtractor

_DOMAIN_KEYWORDS = {
    "linkedin_url": ("linkedin.com",),
    "twitter_url": ("twitter.com", "x.com"),
    "crunchbase_url": ("crunchbase.com",),
    "g2_url": ("g2.com",),
    "capterra_url": ("capterra.com",),
    "youtube_url": ("youtube.com",),
}

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")
_BARE_URL_RE = re.compile(r"https?://[^\s)]+")


class SocialLinksExtract(DataPointExtractor):
    name = "social_links_extract"

    def extract(self, markdown: str, context: dict):
        result = {key: None for key in _DOMAIN_KEYWORDS}

        urls = [url for _, url in _MARKDOWN_LINK_RE.findall(markdown)]
        if not urls:
            urls = _BARE_URL_RE.findall(markdown)

        for url in urls:
            self._classify(url, result)
        self._last_source = "markdown" if any(result.values()) else None
        return result

    @staticmethod
    def _classify(url: str, result: dict) -> None:
        lowered = url.lower()
        for key, keywords in _DOMAIN_KEYWORDS.items():
            if result[key] is None and any(keyword in lowered for keyword in keywords):
                result[key] = url
