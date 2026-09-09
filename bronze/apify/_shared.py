"""Small helpers shared by every bronze/apify/*_scrape.py module - split
out once linkedin_profile_scrape.py needed the same processed-dir and
URL-normalization logic linkedin_company_scrape.py already had, rather
than a third near-identical copy."""
import os
from typing import Any, Optional

import pandas as pd

# Mirrors bronze/apify/_http.py's own "anchor to this file's location, not
# caller's cwd" pattern - three dirname() calls up from bronze/apify/ to
# the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def client_processed_dir(client_id: str) -> str:
    """client_context/clients/<client_id>/processed/ - where every
    Artemis-pipeline CSV for a given client belongs, per
    bronze/CONVENTIONS.md."""
    return os.path.join(_REPO_ROOT, "client_context", "clients", client_id, "processed")


def normalize_url(url: Any) -> Optional[str]:
    """Trailing-slash-safe comparison key. Every harvestapi actor used in
    bronze/apify/ echoes an input URL back with a trailing slash added (or,
    for linkedin-profile-scraper, via a differently-shaped field entirely -
    see linkedin_profile_scrape.py's own docstring) - never join on a raw
    string match without normalizing both sides first."""
    if not url or not isinstance(url, str):
        return None
    return url.rstrip("/")


def write_csv_with_lock_fallback(df: pd.DataFrame, canonical_path: str, max_versions: int = 5) -> str:
    """Writes to `canonical_path`; if that's locked open elsewhere (e.g. in
    Excel), falls back to `<step>.vN.csv` per bronze/CONVENTIONS.md rule 6
    - a transient state to be manually consolidated back to the canonical
    name once whatever's holding the lock is closed, not a shape to keep
    around."""
    root, ext = os.path.splitext(canonical_path)
    for candidate in [canonical_path] + [f"{root}.v{n}{ext}" for n in range(2, max_versions + 1)]:
        try:
            df.to_csv(candidate, index=False)
            return candidate
        except PermissionError:
            continue
    raise PermissionError(f"could not write {canonical_path} - it and every .vN fallback are locked")
