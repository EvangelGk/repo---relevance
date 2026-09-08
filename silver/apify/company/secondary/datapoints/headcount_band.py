"""function_headcount_band(headcount: int | None) -> band: str | None

Buckets a raw headcount (from `apify/company/universal.headcount`) into
LinkedIn's own public company-size brackets, so this pipeline's bands read
the same way a reviewer would already expect from looking a company up on
LinkedIn directly - not an invented cutoff.
"""
from typing import Optional

_BANDS = (
    (10, "1-10"),
    (50, "11-50"),
    (200, "51-200"),
    (500, "201-500"),
    (1000, "501-1000"),
    (5000, "1001-5000"),
    (10000, "5001-10000"),
)
_OVER_MAX = "10001+"


def function_headcount_band(headcount: Optional[int]) -> Optional[str]:
    if headcount is None:
        return None
    if headcount < 0:
        raise ValueError(f"headcount cannot be negative: {headcount}")
    for ceiling, label in _BANDS:
        if headcount <= ceiling:
            return label
    return _OVER_MAX
