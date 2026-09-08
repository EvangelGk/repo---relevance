"""function_seniority(job_title: str | None) -> str | None

Keyword-ladder classification of a raw job title into an operating-company
seniority enum: C_LEVEL, VP, DIRECTOR, MANAGER, IC. Deliberately NOT reused
by `fund_role_normalize.py` - VC/PE title ladders don't map onto this
enum (see that module's docstring).

Referenced by `silver/people/connector.py` but did not exist as a file
until 2026-09-08 - the connector previously (incorrectly) treated
`seniority` as a flat Apify passthrough field, which isn't real: LinkedIn
only ever returns a free-text title, never a seniority enum directly.
"""
import re
from typing import Optional

_C_LEVEL = re.compile(r"\b(chief|ceo|cfo|coo|cto|cmo|cpo|cro|president|founder|co-founder)\b", re.I)
_VP = re.compile(r"\b(vp|vice president|svp|evp)\b", re.I)
_DIRECTOR = re.compile(r"\b(director|head of)\b", re.I)
_MANAGER = re.compile(r"\b(manager|lead|supervisor)\b", re.I)


def function_seniority(job_title: Optional[str]) -> Optional[str]:
    if not job_title:
        return None
    text = job_title.strip()
    if not text:
        return None
    if _C_LEVEL.search(text):
        return "C_LEVEL"
    if _VP.search(text):
        return "VP"
    if _DIRECTOR.search(text):
        return "DIRECTOR"
    if _MANAGER.search(text):
        return "MANAGER"
    return "IC"
