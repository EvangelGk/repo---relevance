"""Bronze-level pulls for LinkedIn *person* profiles, aimed at the signals
needed for activity-based profile prioritization: post volume/recency/
engagement over a trailing window, and follower/connection counts. Two
thin, actor-specific wrappers around bronze/apify/run_actor.py (same
pattern as bronze/apify/linkedin_company_scrape.py) - no single harvestapi
actor returns both profile metadata and post activity together (confirmed
against each actor's own input-schema page, 2026-09-09), so this is two
actors, not one.

Deliberately stops at the bronze pull: raw dataset items back, unflattened,
per bronze/apify/run_actor.py's own rule. Turning these into a combined
priority score (posting frequency + engagement + a follower/connection
"sweet spot" check) is an explicitly separate, not-yet-scoped step - this
module's job is "find the right actor(s) and return the right datapoints,"
nothing more.

`scrape_linkedin_profiles()` - harvestapi/linkedin-profile-scraper
(api id harvestapi~linkedin-profile-scraper, confirmed live 2026-09-09;
same slash-vs-tilde gotcha as every other harvestapi actor here). Returns
profile items including `followerCount` and `connectionsCount`. Run with
`profileScraperMode="Profile details no email ($4 per 1k)"` - the cheaper
of the two documented modes; email reveal isn't needed for activity
tracking and Prospeo's enrich_person.py is already this repo's dedicated
(and cheaper-per-email) path for that.

**Confirmed live, 2026-09-09, against a real 39-profile batch (client
`synthesa`)**: a returned item's own `linkedinUrl` field is NOT a safe
join key back to the URL that was requested - it's LinkedIn's current
*canonical* URL for that profile, which can differ from an older/renamed
vanity URL you queried with (e.g. querying
".../in/barry-cohen-76031218" came back with
`linkedinUrl=".../in/barry-cohen-founder-76031218"`; one profile came back
with `linkedinUrl=None` entirely - private/restricted, still a real item,
not a missing one). Joining on `linkedinUrl` silently dropped 5/39 rows in
that run. The reliable join key is each item's own
`originalQuery["url"]`, which always echoes the exact string that was
sent - use that, not `linkedinUrl`, when matching results back to input
rows (same trailing-slash-normalize-before-comparing discipline as
bronze/apify/_shared.normalize_url - see `_profile_join_key` below).

`scrape_linkedin_profile_posts()` - harvestapi/linkedin-profile-posts
(api id harvestapi~linkedin-profile-posts, confirmed live 2026-09-09).
Returns one item per post, each with `postedAt.date`/`postedAt.timestamp`
and `engagement.likes`/`engagement.comments`/`engagement.shares` - exactly
what's needed downstream to compute posting frequency and engagement
over a window, without this module doing any of that math itself. The
actor's own `postedLimit` field only offers '24h'/'week'/'month' presets
(no 6-month option), so a 6-month cutoff is expressed as `postedLimitDate`
(an explicit ISO date) instead - `_months_ago_iso()` computes that cutoff
with real calendar-month arithmetic (via `calendar.monthrange`), not a
`days=30*months` approximation, which would silently drift the cutoff by
several days per profile scraped months apart. `max_posts` defaults to 0
(all posts within the window) since a frequency count needs every post in
range, not a truncated sample - this makes the actor's own per-post
pricing ($2/1k posts) the real cost driver for an active poster, not a
fixed per-profile cost; worth knowing before scraping a large batch.

**Bronze-CSV contract for the profile-details half, added 2026-09-09**
(`scrape_linkedin_profile_posts()` doesn't have one of these yet - no
identity-spine/file-naming decision has been made for the posts side):
`run_apify_person_profile_bronze(client_id)` follows the same fixed-path
pattern as linkedin_company_scrape.py's `run_apify_linkedin_bronze()`, but
keyed on `clay_profile_id` (this module's identity spine is people, not
companies) and reading from the client's Prospeo bronze output rather than
a company table, since that's where a person's `linkedin_url` actually
comes from in this pipeline:

    input:  client_context/clients/<client_id>/processed/<client_id>_prospeo_bronze.csv
            - must contain clay_profile_id, name, linkedin_url.
    output: client_context/clients/<client_id>/processed/<client_id>_person_profile_apify_bronze.csv
            - clay_profile_id, name, linkedin_url,
              person_profile_apify_bronze_json (the actor's raw profile
              dict, joined via `_profile_join_key` - i.e. `originalQuery`,
              not `linkedinUrl` - or empty if the row had no linkedin_url
              or LinkedIn had nothing for it; every input row still gets a
              row, per this repo's "always return a row" convention).

Confirmed live, 2026-09-09, against the real `synthesa` batch this
function was built from: 39/39 profiles joined correctly once the join
switched from `linkedinUrl` to `originalQuery["url"]`.
"""
import argparse
import calendar
import datetime
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from ._shared import client_processed_dir, normalize_url, write_csv_with_lock_fallback
from .run_actor import run_actor

PROFILE_ACTOR_ID = "harvestapi~linkedin-profile-scraper"
PROFILE_POSTS_ACTOR_ID = "harvestapi~linkedin-profile-posts"

# The exact enum-option string harvestapi/linkedin-profile-scraper expects
# for its (select-style) profileScraperMode field - confirmed against the
# actor's own input-schema page, 2026-09-09.
PROFILE_SCRAPER_MODE_NO_EMAIL = "Profile details no email ($4 per 1k)"

SPINE_COLUMNS = ["clay_profile_id", "name", "linkedin_url"]
RAW_COLUMN = "person_profile_apify_bronze_json"


def _months_ago_iso(months: int, today: Optional[datetime.date] = None) -> str:
    """Real calendar-month subtraction (e.g. 2026-08-31 minus 6 months ->
    2026-02-28), not a `days=30*months` approximation - the latter drifts
    the cutoff date by several days depending on which months it spans,
    which would make "posts in the last 6 months" inconsistent from one
    scrape run to the next."""
    today = today or datetime.date.today()
    month_index = today.month - 1 - months
    year = today.year + month_index // 12
    month = month_index % 12 + 1
    day = min(today.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day).isoformat()


def scrape_linkedin_profiles(
    linkedin_urls: List[str],
    timeout_seconds: int = 300,
) -> List[Dict[str, Any]]:
    """linkedin_urls: full LinkedIn profile URLs (e.g.
    "https://www.linkedin.com/in/williamhgates"). Falsy entries dropped,
    the rest deduped before the call - same "don't double-pay for the same
    row" reasoning as scrape_linkedin_companies(). Returns the actor's raw
    profile dicts (followerCount, connectionsCount, headline, experience,
    ... - unflattened), one per URL LinkedIn had a profile for."""
    deduped = sorted({url for url in linkedin_urls if url})
    if not deduped:
        return []
    payload = {"profileScraperMode": PROFILE_SCRAPER_MODE_NO_EMAIL, "urls": deduped}
    return run_actor(PROFILE_ACTOR_ID, payload, timeout_seconds=timeout_seconds)


def scrape_linkedin_profile_posts(
    linkedin_urls: List[str],
    months: int = 6,
    max_posts: int = 0,
    timeout_seconds: int = 300,
) -> List[Dict[str, Any]]:
    """linkedin_urls: full LinkedIn profile URLs. `months` sets the
    `postedLimitDate` cutoff (default: last 6 months, per real
    calendar-month arithmetic - see _months_ago_iso). `max_posts` is
    passed through as the actor's own per-profile cap; 0 (the default)
    means "every post in the window," which is what a frequency count
    needs - pass a positive number only if you deliberately want a
    truncated sample instead. Returns the actor's raw post dicts
    (postedAt.date, engagement.likes/comments/shares, content, ... -
    unflattened), one per post found in the window, across all URLs
    combined (each item's own `author`/`linkedinUrl` field is what
    identifies which profile it came from)."""
    deduped = sorted({url for url in linkedin_urls if url})
    if not deduped:
        return []
    payload = {
        "targetUrls": deduped,
        "postedLimitDate": _months_ago_iso(months),
        "maxPosts": max_posts,
    }
    return run_actor(PROFILE_POSTS_ACTOR_ID, payload, timeout_seconds=timeout_seconds)


def prospeo_bronze_filename(client_id: str) -> str:
    """<client_id>_prospeo_bronze.csv - the fixed input filename this step
    reads (Prospeo's own bronze output is where a person's linkedin_url
    comes from in this pipeline, not a generic people table)."""
    return f"{client_id}_prospeo_bronze.csv"


def person_profile_apify_bronze_filename(client_id: str) -> str:
    """<client_id>_person_profile_apify_bronze.csv - the fixed output
    filename this step writes."""
    return f"{client_id}_person_profile_apify_bronze.csv"


def _profile_join_key(item: Dict[str, Any]) -> Optional[str]:
    """The actor's own `linkedinUrl` output field is NOT a safe join key
    (see this module's docstring) - `originalQuery["url"]` is."""
    return normalize_url((item.get("originalQuery") or {}).get("url"))


def build_person_profile_apify_bronze_rows(spine_df: pd.DataFrame, timeout_seconds: int = 300) -> pd.DataFrame:
    """Takes a DataFrame with (at least) SPINE_COLUMNS, scrapes every
    non-empty `linkedin_url`, and returns exactly SPINE_COLUMNS +
    RAW_COLUMN - never any other input column - per bronze/CONVENTIONS.md
    rules 2-4, generalized here from companies to people. A row with no
    `linkedin_url`, or whose `linkedin_url` LinkedIn has nothing for, still
    gets a row, with `RAW_COLUMN` empty."""
    missing = [c for c in SPINE_COLUMNS if c not in spine_df.columns]
    if missing:
        raise ValueError(f"input is missing required identity-spine column(s): {missing}")

    urls = spine_df["linkedin_url"].dropna().tolist()
    items = scrape_linkedin_profiles(urls, timeout_seconds=timeout_seconds)
    by_url = {_profile_join_key(item): item for item in items if _profile_join_key(item)}

    out = spine_df[SPINE_COLUMNS].copy()
    out[RAW_COLUMN] = out["linkedin_url"].map(lambda u: by_url.get(normalize_url(u)))
    return out


def run_apify_person_profile_bronze(client_id: str, timeout_seconds: int = 300) -> str:
    """The fixed Artemis-orchestration entry point for this step: reads
    <client_id>_prospeo_bronze.csv and writes
    <client_id>_person_profile_apify_bronze.csv, both under
    client_processed_dir(client_id) - see this module's own docstring for
    the exact contract. Returns the path actually written to (the
    canonical path, unless it was locked - see
    write_csv_with_lock_fallback). Raises FileNotFoundError if the input
    file isn't there yet (e.g. Prospeo's own bronze step hasn't run),
    ValueError if it's missing a required identity-spine column."""
    processed_dir = client_processed_dir(client_id)
    in_path = os.path.join(processed_dir, prospeo_bronze_filename(client_id))
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"{in_path} not found - expected {prospeo_bronze_filename(client_id)}")

    spine_df = pd.read_csv(in_path)
    out_df = build_person_profile_apify_bronze_rows(spine_df, timeout_seconds=timeout_seconds)

    os.makedirs(processed_dir, exist_ok=True)
    canonical_path = os.path.join(processed_dir, person_profile_apify_bronze_filename(client_id))
    return write_csv_with_lock_fallback(out_df, canonical_path)


def _has_no_end_date(end_date: Optional[Dict[str, Any]]) -> bool:
    """An experience entry's `endDate` is always present as a dict for a
    real entry (confirmed live, 2026-09-09, across 340 experience entries
    in the synthesa batch - never a missing key or bare None) - a current
    role's `endDate` has no `month`/`year` (harvestapi renders it as
    `{"text": "Present"}`), while a past role's does. Checking for the
    absence of month/year, rather than matching the literal text "Present",
    avoids depending on that text staying in English."""
    if not end_date:
        return True
    return end_date.get("month") is None and end_date.get("year") is None


def _experience_matches_company(
    experience_entry: Dict[str, Any],
    company_name: Optional[str],
    company_linkedin_url: Optional[str],
) -> bool:
    if company_linkedin_url:
        entry_url = normalize_url(experience_entry.get("companyLinkedinUrl"))
        if entry_url and entry_url == normalize_url(company_linkedin_url):
            return True
    if company_name:
        entry_name = (experience_entry.get("companyName") or "").strip().casefold()
        if entry_name and entry_name == company_name.strip().casefold():
            return True
    return False


def is_current_at_company(
    profile: Optional[Dict[str, Any]],
    company_name: Optional[str] = None,
    company_linkedin_url: Optional[str] = None,
) -> Optional[bool]:
    """Is this person still, right now, in the role that matched
    `company_name` and/or `company_linkedin_url` on their profile's
    `experience` list (from scrape_linkedin_profiles()'s raw output)?
    Matching an experience entry needs only one of the two identifiers to
    line up (an exact, case-insensitive match) - same "one identifier is
    enough" spirit as bronze/prospeo/search.py's own domain-then-name
    company match, generalized here to "either, not necessarily both."

    Returns:
    - `True` - at least one matching experience entry has no end date
      (still there).
    - `False` - one or more experience entries matched, but every match
      has ended.
    - `None` - no experience entry matched at all (nothing to check
      recency against - not evidence of anything, don't treat as False).

    Raises ValueError if neither `company_name` nor `company_linkedin_url`
    is given - there's nothing to match against. `profile=None` (e.g. a
    row whose `person_profile_apify_bronze_json` came back empty) returns
    `None`, same as "no match found"."""
    if not company_name and not company_linkedin_url:
        raise ValueError("must provide company_name and/or company_linkedin_url to match against")
    if not profile:
        return None

    matches = [
        exp
        for exp in (profile.get("experience") or [])
        if _experience_matches_company(exp, company_name, company_linkedin_url)
    ]
    if not matches:
        return None
    return any(_has_no_end_date(exp.get("endDate")) for exp in matches)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Artemis bronze step: <client_id>_prospeo_bronze.csv -> "
            "Apify harvestapi/linkedin-profile-scraper -> <client_id>_person_profile_apify_bronze.csv"
        )
    )
    parser.add_argument("client_id", help="matches client_context/clients/<client_id>.json")
    args = parser.parse_args()

    out_path = run_apify_person_profile_bronze(args.client_id)
    df = pd.read_csv(out_path)
    found = df[RAW_COLUMN].notna().sum()
    print(f"scraped {found}/{len(df)} profiles, wrote {out_path}")


if __name__ == "__main__":
    main()
