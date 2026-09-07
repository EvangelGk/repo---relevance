"""function_careers_page_parse(Firecrawl markdown of /careers or /jobs) ->
array<{title, department, location, posted_date}>

An independent hiring-signal source to reconcile against LinkedIn's flat
open-roles count - richer, since it gives per-role department/location
that a headcount number alone never does. Scoped to a careers-shaped
section only, matched against a broader set of headings than just
"Careers" (Jobs / Open Positions / Open Roles / We're Hiring / Join Us) -
if none of those headings are present, this returns [] rather than
scanning the whole page, since a loose per-line parser run over arbitrary
content would misread ordinary bullet lists as fake job postings.

Two-pass parsing (added 2026-09-08, "provides needed info if normalized
properly"): the original strict format - exactly
"TITLE — DEPARTMENT — LOCATION — Posted YYYY-MM-DD" - almost never appears
verbatim on a real scraped careers page, so it was silently returning []
even ON genuine careers pages. Pass 1 still tries that strict format
first (cheap, unambiguous when present); pass 2 only runs if pass 1 found
nothing, and degrades gracefully - title is the only field it insists on,
department/location/posted_date are extracted opportunistically from
whatever delimiters, parenthetical locations, and known department words
are actually present, and left as None rather than failing the whole line.

Pass 1 is matched per-line (split on "\n"), not as one MULTILINE findall
over the whole section - a bug found 2026-09-08 by actually inspecting
real output (not just a len() assertion, which is all the old test
checked): a single findall() over the whole section let the whitespace
before the first "—"/"-" separator absorb the blank line after the "## Careers"
heading, and the char class `[—-]` then matched a role line's own leading
"- " bullet marker as if it were a field separator - silently shifting
every field over by one on any bulleted line and, worse, splicing the
heading text itself in as a bogus first "role." Per-line matching makes
that class of cross-line chaining structurally impossible.
"""
import re

from ..base import DataPointExtractor

_SECTION_RE = re.compile(
    r"^##\s*(?:careers|jobs|open\s+(?:positions|roles)|we'?re\s+hiring|join\s+(?:us|our\s+team))\b"
    r".*?(?=^##\s|\Z)",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
_STRICT_ROLE_LINE_RE = re.compile(
    r"^(.+?)\s+[—-]\s+(.+?)\s+[—-]\s+(.+?)\s+[—-]\s+Posted\s+(\d{4}-\d{2}-\d{2})\s*$"
)
_LEADING_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_LOOSE_BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<body>[^\n]+)$", re.MULTILINE)
_LOOSE_HEADING_RE = re.compile(r"^#{3,4}\s+(?P<body>[^\n]+)$", re.MULTILINE)
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_TRAILING_PAREN_RE = re.compile(r"\(([^)]+)\)\s*$")
_SPLIT_RE = re.compile(r"\s*[—|]\s*|\s+-\s+|\s*,\s*")
_KNOWN_DEPARTMENTS = {
    "engineering", "sales", "marketing", "design", "product", "support",
    "customer success", "operations", "finance", "hr", "people", "legal",
    "data", "analytics", "recruiting", "talent",
}


def _parse_loose_role_line(raw_body: str):
    body = re.sub(r"[*_`]", "", raw_body).strip()
    if not body:
        return None

    posted_match = _DATE_RE.search(body)
    posted_date = posted_match.group(0) if posted_match else None
    if posted_match:
        body = body[: posted_match.start()].strip()

    location = None
    paren_match = _TRAILING_PAREN_RE.search(body)
    if paren_match:
        location = paren_match.group(1).strip()
        body = body[: paren_match.start()].strip()

    parts = [p.strip() for p in _SPLIT_RE.split(body) if p.strip()]
    if not parts:
        return None

    title = parts[0]
    department = None
    for part in parts[1:]:
        if part.lower() in _KNOWN_DEPARTMENTS:
            department = part
        elif location is None:
            location = part

    if not (3 <= len(title) <= 80) or len(title.split()) > 8:
        return None  # doesn't look like a plausible job title

    return {
        "title": title,
        "department": department,
        "location": location,
        "posted_date": posted_date,
    }


def _parse_strict_role_line(line: str):
    line = _LEADING_BULLET_RE.sub("", line).strip()
    match = _STRICT_ROLE_LINE_RE.match(line)
    if not match:
        return None
    title, department, location, posted_date = match.groups()
    return {
        "title": title.replace("*", "").strip(),
        "department": department.replace("*", "").strip() or None,
        "location": location.replace("*", "").strip() or None,
        "posted_date": posted_date,
    }


class CareersPageParse(DataPointExtractor):
    name = "careers_page_parse"

    def extract(self, markdown: str, context: dict):
        section_match = _SECTION_RE.search(markdown)
        if not section_match:
            self._last_source = None
            return []
        section = section_match.group(0)

        roles = [
            parsed
            for line in section.splitlines()
            if (parsed := _parse_strict_role_line(line)) is not None
        ]

        if not roles:
            seen_titles = set()
            for pattern in (_LOOSE_HEADING_RE, _LOOSE_BULLET_RE):
                for match in pattern.finditer(section):
                    parsed = _parse_loose_role_line(match.group("body"))
                    if parsed and parsed["title"].lower() not in seen_titles:
                        seen_titles.add(parsed["title"].lower())
                        roles.append(parsed)

        self._last_source = "markdown" if roles else None
        return roles
