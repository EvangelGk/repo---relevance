"""Shared helper for this datapoints/ package only - not a cross-source
utility."""
from typing import Any, Dict, Optional


def first(raw: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None
