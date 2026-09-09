"""run_client_search_and_scrape(): the glue between bronze/clay's company
search and bronze/firecrawl's per-domain scrape, flagged as "a separate
step and not this function's job" in bronze/clay/search.py's docstring and
CLAUDE.md's 2026-09-08 addition.

For each company Clay's search returns, scrapes its domain via Firecrawl
and runs the result through SilverOrchestrator.process_page() - so a
ClientContext turns into a scored, gated DataFrame/CSV in one call, with
no manual export/import step through Clay's own UI and no Apify
involvement (Apify is a separate actor-based source - see silver/apify/ -
not part of this domain-to-markdown path).

A company missing a domain, or a Firecrawl failure on one domain, does not
abort the run - it becomes one visibly-flagged row (mirroring
SilverOrchestrator.process_page()'s own "always return a row" contract),
so a partial run's audit trail still explains every input. A Clay-level
failure (ClayAPIError/ClayBudgetExhausted) is NOT caught here and aborts
the whole run - per bronze/clay/_http.py's own docstring, retrying a
budget-exhausted call just spends the same exhausted budget again.

**Added 2026-09-09**: run_people_search_for_batch() and run_full_pipeline()
extend this into "Clay company search -> Firecrawl scrape -> Silver gate
-> Prospeo people search," per company row, in one call - the "make
people search an automatic part of the process" ask from the terminal
conversation that also added ClientContext's people_* fields and
bronze/prospeo/search.py. run_client_search_and_scrape() itself is
unchanged (still returns just the company DataFrame) so existing callers/
tests aren't affected; run_full_pipeline() is the new combined entry
point.

Run from the terminal:
    poetry run python -m bronze.pipeline example-client
    poetry run python -m bronze.pipeline example-client --out companies.csv --people-out people.csv
"""
import argparse
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from bronze.clay.search import run_company_search
from bronze.firecrawl._http import FirecrawlAPIError
from bronze.firecrawl.scrape import scrape_url
from bronze.prospeo.search import run_people_search_for_company
from client_context.schema import ClientContext, load_client_context
from silver.firecrawl import Firecrawl
from silver.silver_orchestrator.orchestrator import SilverOrchestrator

_CLIENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "client_context", "clients")


def run_client_search_and_scrape(
    context: ClientContext,
    orchestrator: Optional[SilverOrchestrator] = None,
) -> pd.DataFrame:
    orchestrator = orchestrator or SilverOrchestrator(Firecrawl())
    search_result = run_company_search(context)

    inputs: List[Dict[str, Any]] = []
    for company in search_result["companies"]:
        domain = company.get("domain")
        if not domain:
            # Clay found the company but returned no domain - still
            # produce a row rather than silently dropping it; empty
            # markdown flows into process_page()'s own empty_response gate.
            inputs.append({"markdown": "", "context": {}})
            continue

        try:
            scraped = scrape_url(f"https://{domain}")
            markdown = scraped["markdown"] or ""
            row_context = {"source_url": scraped["source_url"]}
        except FirecrawlAPIError:
            # One bad domain shouldn't sink the batch.
            markdown = ""
            row_context = {"source_url": f"https://{domain}"}

        inputs.append({"markdown": markdown, "context": row_context})

    return orchestrator.process_batch(inputs)


def run_people_search_for_batch(company_df: pd.DataFrame, context: ClientContext) -> pd.DataFrame:
    """The "search Prospeo for people at each company" half of the
    automatic pipeline - one Prospeo call per company row that passed the
    Silver gate (see run_client_search_and_scrape), via
    bronze/prospeo/search.py's domain-then-name fallback. A company row
    with `is_valid_row=False` is skipped entirely: no reason to spend a
    people-search call sourcing contacts at a company this pipeline has
    already flagged as not a real match.

    Returns one row per matched person, each tagged with
    `company_domain_normalize` (the join key back to `company_df`) and
    `matched_by` ("domain"/"name") - an empty DataFrame if no company row
    both passed the gate and matched anyone.

    Auto-enrichment (revealing email/mobile via
    bronze/prospeo/enrich_person.py) is deliberately NOT done here yet -
    see ClientContext.people_enrich_min_quality_score's docstring; wiring
    it in is a follow-up once these search results have been reviewed
    against a real Prospeo account, not silently bundled into this
    function."""
    rows: List[Dict[str, Any]] = []
    for _, company in company_df.iterrows():
        if not company.get("is_valid_row", False):
            continue
        result = run_people_search_for_company(company.to_dict(), context)
        for person in result["people"]:
            rows.append(
                {
                    "company_domain_normalize": company.get("domain_normalize"),
                    "matched_by": result["matched_by"],
                    **person,
                }
            )
    return pd.DataFrame(rows)


def run_full_pipeline(
    context: ClientContext, orchestrator: Optional[SilverOrchestrator] = None
) -> Dict[str, pd.DataFrame]:
    """Clay company search -> Firecrawl scrape -> SilverOrchestrator gate
    -> Prospeo people search, in one call - the "automatic part of the
    process" entry point. Returns {"companies": ..., "people": ...}."""
    company_df = run_client_search_and_scrape(context, orchestrator=orchestrator)
    people_df = run_people_search_for_batch(company_df, context)
    return {"companies": company_df, "people": people_df}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clay search -> per-domain Firecrawl scrape -> SilverOrchestrator -> Prospeo people search"
    )
    parser.add_argument("client_id", help="filename (without .json) under client_context/clients/")
    parser.add_argument("--out", default=None, help="companies CSV path to write; prints to stdout if omitted")
    parser.add_argument("--people-out", default=None, help="people CSV path to write; skipped if omitted")
    args = parser.parse_args()

    path = os.path.join(_CLIENTS_DIR, f"{args.client_id}.json")
    context = load_client_context(path)
    result = run_full_pipeline(context)
    companies_df, people_df = result["companies"], result["people"]

    if args.out:
        companies_df.to_csv(args.out, index=False)
        print(f"wrote {len(companies_df)} company rows to {args.out}")
    else:
        print(companies_df.to_csv(index=False))

    if args.people_out:
        people_df.to_csv(args.people_out, index=False)
        print(f"wrote {len(people_df)} people rows to {args.people_out}")


if __name__ == "__main__":
    main()
