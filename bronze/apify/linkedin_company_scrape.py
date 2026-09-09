"""Runs harvestapi's "Linkedin Company Details Scraper (No Cookies) [Bulk]"
actor against a batch of LinkedIn company URLs - a thin, actor-specific
wrapper around bronze/apify/run_actor.py, which stays deliberately generic
about actor choice (see its own docstring).

Actor id confirmed live against apify.com, 2026-09-09: the store page
(apify.com/harvestapi/linkedin-company) uses the slash form, but the API
needs the tilde form - same "store page vs. API id" gotcha run_actor.py's
docstring already flags for apify/hello-world -> apify~hello-world.

Input/output shape confirmed against the actor's own input-schema page
(apify.com/harvestapi/linkedin-company/input-schema), also 2026-09-09:
    input:  {"companies": ["https://www.linkedin.com/company/...", ...]}
    output: one dataset item per company found, each item's `linkedinUrl`
            field echoing back the input URL (used below to join actor
            output back onto the row it came from).

Confirmed live, 2026-09-09, against a real client CSV: the actor
normalizes its echoed-back `linkedinUrl` to always end in a trailing "/"
(e.g. input "...company/cex-io" comes back as "...company/cex-io/"), even
when the input URL didn't have one. Both sides of the join below are
trailing-slash-stripped before comparing (`_shared.normalize_url`); the
first live run of this module (pre-fix) silently joined 0/100 rows for
exactly this reason, so don't remove the normalization thinking it's
unnecessary.

**Output shape follows bronze/CONVENTIONS.md** (read that file for the
full rationale): the identity spine (`clay_company_id`, `name`, `domain`,
`linkedin_url`) rides along as real columns, and everything this module
itself produces goes into exactly one unflattened JSON column,
`apify_bronze_json` - no other original company field (industry,
description, funding range, ...) is carried through. That full metadata
lives in the client's own source company list
(`<client_id>_company_table_v1.csv`) and gets joined back in by
`clay_company_id` at a later, final merge step - not here. Firecrawl's
bronze step reads that same company table independently (its own
`<client_id>_firecrawl_bronze.csv`, not chained through this module) -
see CONVENTIONS.md rule 6.

**Artemis orchestration contract, file naming revised 2026-09-09**: this
is meant to be one callable piece of the future Artemis pipeline (see
ARTEMIS_CONTEXT.md), so its input and output are fixed by naming
convention rather than left to caller-supplied paths -
`run_apify_linkedin_bronze(client_id)` is that fixed entry point:

    input:  client_context/clients/<client_id>/processed/<client_id>_company_table_v1.csv
            - must contain clay_company_id, name, domain, linkedin_url.
    output: client_context/clients/<client_id>/processed/<client_id>_apify_bronze.csv
            - clay_company_id, name, domain, linkedin_url,
              apify_bronze_json (the actor's raw dict for that row's
              linkedin_url, or empty if LinkedIn had nothing for it -
              never dropped, matching this repo's "always return a row"
              convention).

Per CONVENTIONS.md rule 5 ("a bronze function's input is exactly what it
needs, not a whole row"), `scrape_linkedin_companies()` itself only ever
sees a plain list of URLs - `run_apify_linkedin_bronze()` is the layer
that reads the identity spine, builds that minimal input, and merges the
result back onto `clay_company_id`.
"""
import argparse
import os
from typing import Any, Dict, List

import pandas as pd

from ._shared import client_processed_dir, normalize_url, write_csv_with_lock_fallback
from .run_actor import run_actor

ACTOR_ID = "harvestapi~linkedin-company"

SPINE_COLUMNS = ["clay_company_id", "name", "domain", "linkedin_url"]
RAW_COLUMN = "apify_bronze_json"


def company_table_filename(client_id: str) -> str:
    """<client_id>_company_table_v1.csv - the fixed input filename this
    step (and, independently, Firecrawl's bronze step) reads."""
    return f"{client_id}_company_table_v1.csv"


def apify_bronze_filename(client_id: str) -> str:
    """<client_id>_apify_bronze.csv - the fixed output filename this step
    writes."""
    return f"{client_id}_apify_bronze.csv"


def scrape_linkedin_companies(
    linkedin_urls: List[str],
    timeout_seconds: int = 300,
) -> List[Dict[str, Any]]:
    """linkedin_urls: full LinkedIn company profile URLs (e.g.
    "https://www.linkedin.com/company/google"). Falsy entries are dropped
    and the rest deduped before the call - the actor bills per company
    (~$3-4/1k), so silently re-scraping the same URL twice would just
    double-charge for the same row. Returns the actor's raw dataset items,
    one per company actually found (a URL LinkedIn has nothing for is
    simply absent from the result, not an error)."""
    deduped = sorted({url for url in linkedin_urls if url})
    if not deduped:
        return []
    return run_actor(ACTOR_ID, {"companies": deduped}, timeout_seconds=timeout_seconds)


def build_apify_linkedin_scrape_rows(spine_df: pd.DataFrame, timeout_seconds: int = 300) -> pd.DataFrame:
    """Takes a DataFrame with (at least) SPINE_COLUMNS, scrapes every
    non-empty `linkedin_url`, and returns exactly SPINE_COLUMNS +
    RAW_COLUMN - never any other input column - per
    bronze/CONVENTIONS.md rules 2-4. A row whose `linkedin_url` LinkedIn
    has nothing for still gets a row, with `RAW_COLUMN` empty."""
    missing = [c for c in SPINE_COLUMNS if c not in spine_df.columns]
    if missing:
        raise ValueError(f"input is missing required identity-spine column(s): {missing}")

    urls = spine_df["linkedin_url"].dropna().tolist()
    items = scrape_linkedin_companies(urls, timeout_seconds=timeout_seconds)
    by_url = {
        normalize_url(item.get("linkedinUrl")): item
        for item in items
        if normalize_url(item.get("linkedinUrl"))
    }

    out = spine_df[SPINE_COLUMNS].copy()
    out[RAW_COLUMN] = out["linkedin_url"].map(lambda u: by_url.get(normalize_url(u)))
    return out


def run_apify_linkedin_bronze(client_id: str, timeout_seconds: int = 300) -> str:
    """The fixed Artemis-orchestration entry point for this step: reads
    clay_companies.csv and writes apify_linkedin_scrape.csv, both under
    client_processed_dir(client_id) - see this module's own docstring for
    the exact contract. Returns the path actually written to (the
    canonical path, unless it was locked - see
    _write_csv_with_lock_fallback). Raises FileNotFoundError if the input
    file isn't there yet (e.g. an earlier Artemis step hasn't produced
    it), ValueError if it's missing a required identity-spine column."""
    processed_dir = client_processed_dir(client_id)
    in_path = os.path.join(processed_dir, company_table_filename(client_id))
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"{in_path} not found - expected {company_table_filename(client_id)}")

    spine_df = pd.read_csv(in_path)
    out_df = build_apify_linkedin_scrape_rows(spine_df, timeout_seconds=timeout_seconds)

    os.makedirs(processed_dir, exist_ok=True)
    canonical_path = os.path.join(processed_dir, apify_bronze_filename(client_id))
    return write_csv_with_lock_fallback(out_df, canonical_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Artemis bronze step: <client_id>_company_table_v1.csv -> "
            "Apify harvestapi/linkedin-company -> <client_id>_apify_bronze.csv"
        )
    )
    parser.add_argument("client_id", help="matches client_context/clients/<client_id>.json")
    args = parser.parse_args()

    out_path = run_apify_linkedin_bronze(args.client_id)
    df = pd.read_csv(out_path)
    found = df[RAW_COLUMN].notna().sum()
    print(f"scraped {found}/{len(df)} companies, wrote {out_path}")


if __name__ == "__main__":
    main()
