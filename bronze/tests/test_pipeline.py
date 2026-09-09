"""Tests for bronze.pipeline.run_client_search_and_scrape - both Clay's and
Firecrawl's HTTP layers are mocked (matching bronze/clay/tests/test_search.py
and bronze/firecrawl's own offline-test convention), so this suite never
makes a real network call."""
from unittest.mock import patch

import pandas as pd

from bronze.firecrawl._http import FirecrawlAPIError
from bronze.pipeline import run_client_search_and_scrape, run_people_search_for_batch
from client_context.schema import ClientContext
from silver.firecrawl import Firecrawl
from silver.silver_orchestrator.dead_letter import DeadLetterQueue
from silver.silver_orchestrator.drift import DriftTracker
from silver.silver_orchestrator.orchestrator import SilverOrchestrator

COMPANY_MD = (
    "# Acme Corp\n\nAcme Corp is a growing analytics company. Acme Corp works "
    "with mid-market retailers to unify their reporting. Acme Corp is based "
    "in Austin, Texas.\n"
)


def _context(**overrides) -> ClientContext:
    defaults = {"client_id": "test", "name": "Test", "limit": 100}
    defaults.update(overrides)
    return ClientContext(**defaults)


def _orchestrator(tmp_path) -> SilverOrchestrator:
    dead_letter = DeadLetterQueue(path=str(tmp_path / "dead_letter.jsonl"))
    drift = DriftTracker(path=str(tmp_path / "quality_history.jsonl"))
    return SilverOrchestrator(Firecrawl(), dead_letter=dead_letter, drift=drift)


def _clay_responses(domains):
    return [
        {"search_id": "s1", "source_type": "companies"},
        {"data": [{"domain": d} for d in domains], "has_more": False},
    ]


def test_scrapes_each_domain_and_produces_one_row_per_company(tmp_path):
    clay_responses = _clay_responses(["acme.com"])
    scrape_response = {
        "data": {
            "markdown": COMPANY_MD,
            "metadata": {"sourceURL": "https://acme.com", "title": "Acme", "statusCode": 200},
        }
    }
    with patch("bronze.clay.search._http.post", side_effect=clay_responses), patch(
        "bronze.firecrawl.scrape._http.post", return_value=scrape_response
    ) as mock_scrape:
        df = run_client_search_and_scrape(_context(), orchestrator=_orchestrator(tmp_path))

    assert len(df) == 1
    assert df.iloc[0]["domain_normalize"] == "acme.com"
    mock_scrape.assert_called_once_with("/scrape", {"url": "https://acme.com", "formats": ["markdown"]})


def test_missing_domain_still_produces_a_visibly_rejected_row(tmp_path):
    clay_responses = [
        {"search_id": "s1", "source_type": "companies"},
        {"data": [{}], "has_more": False},
    ]
    with patch("bronze.clay.search._http.post", side_effect=clay_responses):
        df = run_client_search_and_scrape(_context(), orchestrator=_orchestrator(tmp_path))

    assert len(df) == 1
    assert df.iloc[0]["is_valid_row"] == False  # noqa: E712


def test_one_failed_scrape_does_not_abort_the_batch(tmp_path):
    clay_responses = _clay_responses(["good.com", "bad.com"])
    good_scrape = {
        "data": {
            "markdown": COMPANY_MD,
            "metadata": {"sourceURL": "https://good.com", "title": "Good", "statusCode": 200},
        }
    }
    with patch("bronze.clay.search._http.post", side_effect=clay_responses), patch(
        "bronze.firecrawl.scrape._http.post", side_effect=[good_scrape, FirecrawlAPIError(500, "boom")]
    ):
        df = run_client_search_and_scrape(_context(), orchestrator=_orchestrator(tmp_path))

    assert len(df) == 2
    assert (df["is_valid_row"] == True).sum() == 1  # noqa: E712


def test_run_people_search_for_batch_skips_invalid_rows_and_tags_matches():
    company_df = pd.DataFrame(
        [
            {"domain_normalize": "good.com", "domain": "good.com", "is_valid_row": True},
            {"domain_normalize": "bad.com", "domain": "bad.com", "is_valid_row": False},
        ]
    )
    context = _context(people_job_title_include=["VP Sales"])
    fake_response = {"results": [{"person_id": "p1"}]}

    with patch("bronze.prospeo.search_person._http.post", return_value=fake_response) as mock_post:
        people_df = run_people_search_for_batch(company_df, context)

    mock_post.assert_called_once()
    assert len(people_df) == 1
    assert people_df.iloc[0]["company_domain_normalize"] == "good.com"
    assert people_df.iloc[0]["matched_by"] == "domain"
    assert people_df.iloc[0]["person_id"] == "p1"


def test_run_people_search_for_batch_empty_when_no_rows_are_valid():
    company_df = pd.DataFrame([{"domain_normalize": "bad.com", "domain": "bad.com", "is_valid_row": False}])
    context = _context(people_job_title_include=["VP Sales"])

    with patch("bronze.prospeo.search_person._http.post") as mock_post:
        people_df = run_people_search_for_batch(company_df, context)

    mock_post.assert_not_called()
    assert people_df.empty
