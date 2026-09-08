"""function_bio_entity_extract(bio_text: str) -> dict

Conservative regex entity extraction from a person's LinkedIn "About"
free text:

    {"mentioned_urls": [...], "mentioned_companies": [...], "mentioned_handles": [...]}

- `mentioned_urls`: any http(s) URL found as-is.
- `mentioned_companies`: text following "at "/"@ " when capitalized
  (e.g. "Building at Acme Corp" -> "Acme Corp"), a narrow heuristic that
  favors precision over recall - this is not a general NER pass.
- `mentioned_handles`: bare "@handle" social mentions (lowercase/mixed-case
  handles) - distinct from the "@" + capitalized-name case above, which
  only fires when the token right after "@" starts with a capital letter.
"""
import re
from typing import Dict, List, Optional

_URL_RE = re.compile(r"https?://[^\s)]+")
_AT_COMPANY_RE = re.compile(r"(?:\bat\s+|@\s*)([A-Z][\w&\-]*(?:\s+[A-Z][\w&\-]*){0,4})")
_HANDLE_RE = re.compile(r"(?<!\w)@(\w{2,30})\b")


def function_bio_entity_extract(bio_text: Optional[str]) -> Dict[str, List[str]]:
    text = bio_text or ""

    urls = _URL_RE.findall(text)

    companies = []
    for match in _AT_COMPANY_RE.finditer(text):
        name = match.group(1).strip()
        if name and name not in companies:
            companies.append(name)

    handles = []
    for match in _HANDLE_RE.finditer(text):
        handle = match.group(1)
        if handle not in handles:
            handles.append(handle)

    return {
        "mentioned_urls": urls,
        "mentioned_companies": companies,
        "mentioned_handles": handles,
    }
