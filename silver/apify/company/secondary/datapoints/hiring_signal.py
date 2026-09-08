"""function_hiring_signal(apify_context: dict) -> signal: str | None

Surfaces an "actively hiring" style signal from Apify's LinkedIn company
data. Reads two candidate keys - `open_roles_count` (int) and
`headcount_growth_pct` (float, e.g. 12.5 for +12.5% over some Apify-defined
window) - falling back gracefully if either is missing.

Exact Apify field names are UNCONFIRMED (no live Apify company sample
pulled in this session) - `open_roles_count` / `headcount_growth_pct` are
placeholders documenting the *shape* this function expects. Whoever wires
this to a real Apify actor output should confirm the real key names and
update the two `.get(...)` calls below; the banding logic itself doesn't
need to change.
"""
from typing import Any, Dict, Optional

_ACTIVE_ROLES_THRESHOLD = 5


def function_hiring_signal(apify_context: Dict[str, Any]) -> Optional[str]:
    apify_context = apify_context or {}
    open_roles = apify_context.get("open_roles_count")
    growth_pct = apify_context.get("headcount_growth_pct")

    if open_roles is not None:
        if open_roles >= _ACTIVE_ROLES_THRESHOLD:
            return "actively_hiring"
        if open_roles > 0:
            return "hiring"
        if growth_pct is None:
            return "not_hiring"

    if growth_pct is not None:
        if growth_pct > 0:
            return "growing"
        if growth_pct < 0:
            return "shrinking"
        return "stable"

    return None
