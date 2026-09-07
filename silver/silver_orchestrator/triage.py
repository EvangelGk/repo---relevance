"""Crawl-issue and content-integrity triage - a richer, ladder-based
replacement/superset of SilverOrchestrator's old single is_company_profile
boolean, adapted from a B2B account-research crawl-extraction prompt (see
the Cowork Project's 2026-09-07 schema-inspiration proposal) into what this
repo can actually see.

Scope note: that source prompt also classified network-layer failures
(dns_failure, page_not_found, ssl errors) from a scraper-metadata object
this repo doesn't have - Firecrawl only ever receives already-fetched
markdown, never a raw HTTP status or a separate metadata blob. Those
categories are deliberately NOT ported here; inventing them from text
patterns alone would be guessing, not grounding. What IS ported is the
subset that's genuinely readable from markdown content: parked-domain
placeholders, under-construction notices, bot/captcha interstitials,
login/paywall gates, cookie-banner-only pages, directory/aggregator
listings, and near-empty scrapes.

Runs BEFORE Firecrawl.run_all() - same layer as the pre-existing
is_company_profile check in orchestrator.py, one step earlier than
schema_gate.py (which validates what a datapoint function actually
returned, not whether the page was worth running at all).
"""
import re
from typing import Tuple

_WHITESPACE_ONLY_RE = re.compile(r"^\s*$")

_PARKED_RE = re.compile(
    r"\b(this domain is for sale|buy this domain|domain parking|"
    r"godaddy|sedo\.com|afternic|namecheap parking|is available for purchase)\b",
    re.IGNORECASE,
)
_UNDER_CONSTRUCTION_RE = re.compile(
    r"\b(coming soon|site under maintenance|under construction|"
    r"launching soon|this site is (?:currently )?being built|deploy your files)\b",
    re.IGNORECASE,
)
_BOT_CHALLENGE_RE = re.compile(
    r"\b(verify you are human|attention required|checking your browser|"
    r"cloudflare|access denied|blocked by an extension|are you a robot|captcha)\b",
    re.IGNORECASE,
)
_LOGIN_REQUIRED_RE = re.compile(
    r"\b(sign in to continue|please log in to view|subscribers only|"
    r"this content is for subscribers|paywall)\b",
    re.IGNORECASE,
)
_COOKIE_BANNER_RE = re.compile(
    r"\b(we use cookies|accept all cookies|cookie (?:policy|consent)|gdpr consent)\b",
    re.IGNORECASE,
)
_LOTTERY_RE = re.compile(r"\b(draw results|winning numbers|lottery|jackpot)\b", re.IGNORECASE)
_LISTING_BLOCK_RE = re.compile(
    r"\b(top\s+\d+\b|\d+\s+(?:best|top)\b|reviews?\s*[:•]?\s*\d(?:\.\d)?\s*/\s*5)\b",
    re.IGNORECASE,
)
_RATING_TOKEN_RE = re.compile(r"\d(?:\.\d)?\s*(?:/\s*5|★|stars?)\b", re.IGNORECASE)

_LOREM_IPSUM_RE = re.compile(r"\blorem ipsum\b", re.IGNORECASE)
_WORDPRESS_DEFAULT_RE = re.compile(
    r"\b(welcome to wordpress|this is your first post|hello world)\b", re.IGNORECASE
)
_PLACEHOLDER_NAME_RE = re.compile(r"\b(john doe|jane smith|jesse n\.?|frankie b\.?)\b", re.IGNORECASE)

# Conservative on purpose - 15 catches genuinely near-empty scrapes without
# swallowing a short-but-real page (a two-sentence "who we are" is still a
# company page, see test_process_page_rejects_snippet_missing_domain, which
# deliberately exercises a ~28-word *genuine* snippet that must NOT be
# caught here - it's meant to reach schema_gate's domain_normalize check).
_EMPTY_PROSE_WORDS = 15
_THIN_PROSE_WORDS = 120


def _word_count(markdown: str) -> int:
    return len(re.findall(r"[A-Za-z']+", markdown))


def _looks_like_directory(text: str) -> bool:
    """Cheap signal: 3+ paragraphs each carrying a rating-like token
    ("4.8/5", 4 stars) alongside listing language ("Top 10 ...") - a
    repeating name+rating+location block is the directory/aggregator
    fingerprint, not a company describing itself once."""
    if not _LISTING_BLOCK_RE.search(text):
        return False
    rated_paragraphs = sum(
        1 for paragraph in re.split(r"\n\s*\n", text) if _RATING_TOKEN_RE.search(paragraph)
    )
    return rated_paragraphs >= 3


def classify_crawl_issue(markdown: str) -> Tuple[str, str]:
    """Return (crawl_issue, crawl_status). crawl_status is "ok"/"partial"
    when crawl_issue is "none", "unusable" for every other issue - first
    match in the precedence ladder wins."""
    markdown = markdown or ""

    if _WHITESPACE_ONLY_RE.match(markdown):
        return "empty_response", "unusable"
    if _PARKED_RE.search(markdown):
        return "parked_or_for_sale", "unusable"
    if _UNDER_CONSTRUCTION_RE.search(markdown):
        return "under_construction", "unusable"
    if _BOT_CHALLENGE_RE.search(markdown):
        return "bot_challenge", "unusable"
    if _LOGIN_REQUIRED_RE.search(markdown):
        return "login_required", "unusable"

    body = markdown
    cookie_match = _COOKIE_BANNER_RE.search(markdown)
    if cookie_match:
        remainder = markdown[cookie_match.end():]
        if _word_count(remainder) < _EMPTY_PROSE_WORDS:
            return "cookie_wall", "unusable"
        body = remainder  # real content follows the banner - judge that, not the banner

    if _LOTTERY_RE.search(body):
        return "non_company_page", "unusable"
    if _looks_like_directory(body):
        return "directory_or_aggregator", "unusable"
    if _word_count(body) < _EMPTY_PROSE_WORDS:
        return "boilerplate_only", "unusable"
    if _word_count(body) < _THIN_PROSE_WORDS:
        return "none", "partial"
    return "none", "ok"


def classify_content_integrity(markdown: str) -> str:
    """Independent of classify_crawl_issue: a page can clear the crawl-
    issue ladder and still be unlaunched theme demo content. Deliberately
    narrower than the source prompt - no "abandoned" (stale-copyright)
    detection, since that needs a trustworthy current-date signal this
    repo's markdown-only input doesn't reconstruct without inventing one."""
    markdown = markdown or ""
    if not markdown.strip():
        return "unknown"
    if _UNDER_CONSTRUCTION_RE.search(markdown):
        return "under_construction"
    if (
        _LOREM_IPSUM_RE.search(markdown)
        or _WORDPRESS_DEFAULT_RE.search(markdown)
        or _PLACEHOLDER_NAME_RE.search(markdown)
    ):
        return "placeholder_or_template"
    return "genuine"
