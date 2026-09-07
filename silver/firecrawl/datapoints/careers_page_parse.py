"""function_careers_page_parse(Firecrawl markdown of /careers or /jobs) ->
array<{title, department, location, posted_date}>

An independent hiring-signal source to reconcile against LinkedIn's flat
open-roles count - richer, since it gives per-role department/location
that a headcount number alone never does. Matches "TITLE - DEPARTMENT -
LOCATION - Posted YYYY-MM-DD" lines regardless of a leading bullet or bold
marker, scoped to the Careers section only (from "## Careers" to the next
"## " heading).
"""
import re

from ..base import DataPointExtractor

_SECTION_RE = re.compile(r"^##\s*Careers\b.*?(?=^##\s|\Z)", re.IGNORECASE | re.MULTILINE | re.DOTALL)
_ROLE_LINE_RE = re.compile(
    r"^\**\s*(.+?)\**\s+[—-]\s+(.+?)\s+[—-]\s+(.+?)\s+[—-]\s+Posted\s+(\d{4}-\d{2}-\d{2})",
    re.MULTILINE,
)


class CareersPageParse(DataPointExtractor):
    name = "careers_page_parse"

    def extract(self, markdown: str, context: dict):
        section_match = _SECTION_RE.search(markdown)
        section = section_match.group(0) if section_match else markdown

        roles = []
        for title, department, location, posted_date in _ROLE_LINE_RE.findall(section):
            roles.append({
                "title": title.replace("*", "").strip(),
                "department": department.replace("*", "").strip() or None,
                "location": location.replace("*", "").strip() or None,
                "posted_date": posted_date,
            })
        self._last_source = "markdown" if roles else None
        return roles
