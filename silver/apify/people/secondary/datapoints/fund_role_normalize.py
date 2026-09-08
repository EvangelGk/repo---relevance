"""function_fund_role_normalize(raw_title: str | None) -> str | None

Maps VC/PE-specific job titles to a fixed fund-role enum. Deliberately
separate from a generic `function_seniority` (Junior/Mid/Senior/Director/
VP/C-Suite style ladder, out of scope here) - fund titles carry
domain-specific meaning a generic seniority ladder would flatten away
(e.g. a "Venture Partner" is not simply "senior", it's a specific,
usually part-time, non-employee role distinct from a "Partner").
"""
import re
from typing import Optional

_CANONICAL = {
    "MANAGING_PARTNER": ("managing partner", "managing director"),
    "GENERAL_PARTNER": ("general partner", "gp"),
    "PARTNER": ("partner",),
    "VENTURE_PARTNER": ("venture partner",),
    "OPERATING_PARTNER": ("operating partner",),
    "PRINCIPAL": ("principal",),
    "VICE_PRESIDENT": ("vice president", "vp"),
    "ASSOCIATE": ("associate",),
    "ANALYST": ("analyst",),
    "SCOUT": ("scout", "venture scout"),
}
# Order matters: check more specific multi-word aliases before the bare
# "partner"/"vp" aliases they'd otherwise be swallowed by.
_ORDERED_CODES = (
    "MANAGING_PARTNER", "GENERAL_PARTNER", "VENTURE_PARTNER", "OPERATING_PARTNER",
    "PARTNER", "VICE_PRESIDENT", "PRINCIPAL", "ASSOCIATE", "ANALYST", "SCOUT",
)


def function_fund_role_normalize(raw_title: Optional[str]) -> Optional[str]:
    if not raw_title or not str(raw_title).strip():
        return None
    cleaned = re.sub(r"\s+", " ", str(raw_title).strip().lower())
    for code in _ORDERED_CODES:
        for alias in _CANONICAL[code]:
            if re.search(r"\b" + re.escape(alias) + r"\b", cleaned):
                return code
    return None
