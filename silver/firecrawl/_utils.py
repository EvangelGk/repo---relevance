"""Shared markdown-parsing helpers used by the datapoint extractors.

Cleaned Firecrawl markdown rarely keeps a full DOM, so these are regex/heuristic
helpers rather than a real HTML parser - each extractor degrades gracefully
(returns None/empty) when the signal it needs didn't survive the clean.
"""
import re

LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^\s)]+)\)")
BARE_URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")
PRICE_RE = re.compile(r"(?:[$€£¥]|USD|EUR|GBP)\s?\d[\d,.]*")


def extract_links(markdown: str):
    """Return [(anchor_text, url), ...] for markdown links and bare URLs."""
    links = [(text.strip(), url) for text, url in LINK_RE.findall(markdown)]
    linked_urls = {url for _, url in links}
    for url in BARE_URL_RE.findall(markdown):
        if url not in linked_urls:
            links.append(("", url))
            linked_urls.add(url)
    return links


def extract_footer(markdown: str, tail_lines: int = 25) -> str:
    """Heuristic: footers live in the last chunk of the page, or under a
    '## Footer' / '### Contact' / '### Legal' heading when one exists."""
    heading_match = re.search(
        r"^#{1,6}\s*(footer|contact|legal)\b.*$", markdown, re.IGNORECASE | re.MULTILINE
    )
    if heading_match:
        return markdown[heading_match.start():]
    lines = markdown.strip().splitlines()
    return "\n".join(lines[-tail_lines:])


def find_section(markdown: str, heading_keywords, max_chars: int = 4000) -> str:
    """Return the text under the first heading whose title matches one of
    heading_keywords, stopping at the next heading of equal-or-higher level."""
    pattern = re.compile(r"^(#{1,6})\s*(.+)$", re.MULTILINE)
    headings = list(pattern.finditer(markdown))
    kw = [k.lower() for k in heading_keywords]
    for i, m in enumerate(headings):
        title = m.group(2).strip().lower()
        if any(k in title for k in kw):
            level = len(m.group(1))
            start = m.end()
            end = len(markdown)
            for nxt in headings[i + 1:]:
                if len(nxt.group(1)) <= level:
                    end = nxt.start()
                    break
            return markdown[start:end][:max_chars]
    return ""
