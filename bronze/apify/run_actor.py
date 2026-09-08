"""Runs a single Apify actor synchronously and returns its dataset items,
unflattened - Artemis step 3 ("pull from source"), the Apify half (Clay's
own search is the other half; see ARTEMIS_CONTEXT.md's step split).

Endpoint confirmed live against docs.apify.com, 2026-09-08:
    POST /v2/acts/{actor_id}/run-sync-get-dataset-items
Runs the actor with `actor_input` as the request body, waits up to
`timeout_seconds` (Apify's own hard ceiling for this convenience endpoint
is 300s), and returns the actor's default dataset items directly as a JSON
array - no separate run-then-poll-then-fetch-dataset round trip needed for
anything that finishes in time.

PLACEHOLDER, deliberately unopinionated about actor choice or item shape:
- Which actor(s) this repo actually uses isn't decided yet - `actor_id` is
  passed in by the caller, not hardcoded here.
- A different actor returns a different item shape (unlike Firecrawl's
  fixed markdown/metadata response), so this returns Apify's raw item
  dicts as-is - no flattening attempted. Per-actor normalization into
  typed fields (mirroring how silver/firecrawl/datapoints/*.py turns raw
  markdown into typed fields) belongs in a separate normalizer module -
  CLAUDE.md already reserves silver/apify/ (currently empty) for this.
  Nothing in bronze/apify/ should grow actor-specific field logic.
- Actors that run longer than the synchronous window aren't handled yet -
  that needs the async run + poll + fetch-dataset flow instead of this
  one-shot call, not yet built (out of scope for this placeholder).
"""
from typing import Any, Dict, List, Optional

from . import _http

# Apify's own hard ceiling for the run-sync-get-dataset-items endpoint.
_MAX_SYNC_TIMEOUT_SECONDS = 300


def run_actor(
    actor_id: str,
    actor_input: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = _MAX_SYNC_TIMEOUT_SECONDS,
) -> List[Dict[str, Any]]:
    """`actor_id` is either the plain actor ID (e.g. "vKg4IjxZbEYTYeW8T")
    or the "username~actor-name" form. Returns the raw dataset items list;
    raises ApifyRunTimedOut (bronze.apify._http) if the actor doesn't
    finish within timeout_seconds."""
    path = f"/acts/{actor_id}/run-sync-get-dataset-items?timeout={timeout_seconds}"
    response = _http.post(path, actor_input or {})
    # The endpoint returns the dataset items array directly - unlike Clay/
    # Firecrawl's {"data": ...}-wrapped responses, there's no envelope key
    # to unwrap here.
    return response if isinstance(response, list) else []
