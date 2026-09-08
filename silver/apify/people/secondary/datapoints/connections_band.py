"""function_connections_band(connections_count: int | None) -> str | None

LinkedIn's own UI never shows an exact count at or above 500 - it shows
"500+". This mirrors that behavior exactly rather than inventing a
different banding scheme: below 500, the exact count as a string; at or
above 500, `"500+"`.
"""
from typing import Optional


def function_connections_band(connections_count: Optional[int]) -> Optional[str]:
    if connections_count is None:
        return None
    if connections_count < 0:
        raise ValueError(f"connections_count cannot be negative: {connections_count}")
    if connections_count >= 500:
        return "500+"
    return str(connections_count)
