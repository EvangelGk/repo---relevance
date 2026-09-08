"""function_company_type_normalize(raw_type: str | None) -> normalized: str | None

Maps LinkedIn's own public "Company Type" values (as shown on a LinkedIn
company page and returned by Apify LinkedIn company scrapers) to a fixed
enum - grounded in LinkedIn's real taxonomy, not invented.
"""
import re
from typing import Optional

_CANONICAL = {
    "PUBLIC_COMPANY": ("public company",),
    "PRIVATELY_HELD": ("privately held", "private company"),
    "NONPROFIT": ("nonprofit", "non-profit", "non profit"),
    "GOVERNMENT_AGENCY": ("government agency",),
    "PARTNERSHIP": ("partnership",),
    "SELF_EMPLOYED": ("self-employed", "self employed"),
    "SOLE_PROPRIETORSHIP": ("sole proprietorship",),
    "EDUCATIONAL_INSTITUTION": ("educational institution", "educational"),
}


def function_company_type_normalize(raw_type: Optional[str]) -> Optional[str]:
    if not raw_type or not str(raw_type).strip():
        return None
    cleaned = re.sub(r"\s+", " ", str(raw_type).strip().lower())
    for code, aliases in _CANONICAL.items():
        if cleaned in aliases:
            return code
    return None
