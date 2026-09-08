"""function_mutual_connections_context(mutual_connections) -> dict

Accepts either an int count or a list of connection dicts (each with at
least a "name" key) - Apify LinkedIn scrapers vary on which shape they
return - and produces a consistent summary:

    {"mutual_count": int, "sample_names": list[str]}

`sample_names` is capped at 3 so a UI can show "John, Priya, Wei + 12
more" without a raw dump of a potentially long list.
"""
from typing import Any, Dict, List, Optional, Union

_SAMPLE_CAP = 3


def function_mutual_connections_context(
    mutual_connections: Optional[Union[int, List[Dict[str, Any]]]],
) -> Dict[str, Any]:
    if mutual_connections is None:
        return {"mutual_count": 0, "sample_names": []}

    if isinstance(mutual_connections, int):
        return {"mutual_count": max(mutual_connections, 0), "sample_names": []}

    names = [c.get("name") for c in mutual_connections if c.get("name")]
    return {"mutual_count": len(mutual_connections), "sample_names": names[:_SAMPLE_CAP]}
