"""Tests for bronze.apify.linkedin_company_scrape - mocks run_actor (one
layer below), matching bronze/apify/tests/test_run_actor.py's own
"mock the thing just below what you're testing" convention. No real
network call, no real CSV cost. Output shape is checked against
bronze/CONVENTIONS.md (identity spine + one JSON column, clay_company_id
as the primary key, <client_id>_<step>.csv file naming)."""
import os
from unittest.mock import patch

import pandas as pd
import pytest

from bronze.apify.linkedin_company_scrape import (
    ACTOR_ID,
    RAW_COLUMN,
    SPINE_COLUMNS,
    apify_bronze_filename,
    build_apify_linkedin_scrape_rows,
    client_processed_dir,
    company_table_filename,
    run_apify_linkedin_bronze,
    scrape_linkedin_companies,
)


def _spine_df(**overrides):
    defaults = {
        "clay_company_id": ["1"],
        "name": ["Acme"],
        "domain": ["acme.com"],
        "linkedin_url": ["https://www.linkedin.com/company/acme"],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


def test_dedupes_and_drops_empty_urls_before_calling_the_actor():
    with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[]) as mock_run:
        scrape_linkedin_companies(
            ["https://www.linkedin.com/company/acme", "", None, "https://www.linkedin.com/company/acme"]
        )

    mock_run.assert_called_once_with(
        ACTOR_ID, {"companies": ["https://www.linkedin.com/company/acme"]}, timeout_seconds=300
    )


def test_empty_input_skips_the_actor_call_entirely():
    with patch("bronze.apify.linkedin_company_scrape.run_actor") as mock_run:
        result = scrape_linkedin_companies([])

    assert result == []
    mock_run.assert_not_called()


def test_output_columns_are_exactly_the_identity_spine_plus_the_json_column():
    """bronze/CONVENTIONS.md rule 4: no other input column (e.g. `size`,
    `industry`) leaks through, even if the caller's DataFrame has one."""
    spine = _spine_df(industry=["Financial Services"], annual_revenue=["75M-200M"])
    with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[]):
        out = build_apify_linkedin_scrape_rows(spine)

    assert list(out.columns) == SPINE_COLUMNS + [RAW_COLUMN]


def test_rows_are_joined_back_to_their_raw_actor_item():
    spine = _spine_df()
    raw_item = {"linkedinUrl": "https://www.linkedin.com/company/acme", "employeeCount": 42}
    with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[raw_item]):
        out = build_apify_linkedin_scrape_rows(spine)

    assert out.loc[0, RAW_COLUMN] == raw_item
    assert out.loc[0, "clay_company_id"] == "1"


def test_a_url_with_no_actor_match_still_produces_a_row():
    spine = _spine_df()
    with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[]):
        out = build_apify_linkedin_scrape_rows(spine)

    assert len(out) == 1
    assert pd.isna(out.loc[0, RAW_COLUMN])


def test_join_tolerates_the_actors_trailing_slash_normalization():
    """Regression test: the actor echoes `linkedinUrl` back with a
    trailing slash even when the input URL didn't have one (confirmed
    live 2026-09-09 - see the module docstring), which silently zeroed
    out every join before this was fixed."""
    spine = _spine_df()
    raw_item = {"linkedinUrl": "https://www.linkedin.com/company/acme/", "employeeCount": 42}
    with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[raw_item]):
        out = build_apify_linkedin_scrape_rows(spine)

    assert out.loc[0, RAW_COLUMN] == raw_item


def test_missing_spine_column_raises_clearly():
    spine = _spine_df().drop(columns=["domain"])
    with pytest.raises(ValueError, match="domain"):
        build_apify_linkedin_scrape_rows(spine)


def test_client_processed_dir_is_under_that_clients_folder():
    path = client_processed_dir("trial-fintech-us-uk")
    assert path.replace("\\", "/").endswith("client_context/clients/trial-fintech-us-uk/processed")


def test_filenames_are_prefixed_with_the_client_id():
    assert company_table_filename("acme-co") == "acme-co_company_table_v1.csv"
    assert apify_bronze_filename("acme-co") == "acme-co_apify_bronze.csv"


def test_run_apify_linkedin_bronze_reads_company_table_and_writes_apify_bronze(tmp_path):
    with patch("bronze.apify._shared._REPO_ROOT", str(tmp_path)):
        processed_dir = client_processed_dir("acme-co")
        os.makedirs(processed_dir, exist_ok=True)
        _spine_df(industry=["Financial Services"]).to_csv(
            os.path.join(processed_dir, "acme-co_company_table_v1.csv"), index=False
        )

        raw_item = {"linkedinUrl": "https://www.linkedin.com/company/acme/", "employeeCount": 7}
        with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[raw_item]):
            out_path = run_apify_linkedin_bronze("acme-co")

        assert out_path == os.path.join(processed_dir, "acme-co_apify_bronze.csv")
        result = pd.read_csv(out_path)
        assert list(result.columns) == SPINE_COLUMNS + [RAW_COLUMN]
        assert result.loc[0, "clay_company_id"] == 1
        assert "employeeCount" in result.loc[0, RAW_COLUMN]


def test_run_apify_linkedin_bronze_raises_clearly_if_company_table_is_missing(tmp_path):
    with patch("bronze.apify._shared._REPO_ROOT", str(tmp_path)):
        with pytest.raises(FileNotFoundError, match="acme-co_company_table_v1.csv"):
            run_apify_linkedin_bronze("acme-co")


def test_run_apify_linkedin_bronze_falls_back_to_a_versioned_file_when_the_canonical_path_is_locked(tmp_path):
    with patch("bronze.apify._shared._REPO_ROOT", str(tmp_path)):
        processed_dir = client_processed_dir("acme-co")
        os.makedirs(processed_dir, exist_ok=True)
        _spine_df().to_csv(os.path.join(processed_dir, "acme-co_company_table_v1.csv"), index=False)
        canonical_path = os.path.join(processed_dir, "acme-co_apify_bronze.csv")
        # Simulate the canonical file being locked open elsewhere (e.g. Excel).
        os.makedirs(canonical_path, exist_ok=True)

        with patch("bronze.apify.linkedin_company_scrape.run_actor", return_value=[]):
            out_path = run_apify_linkedin_bronze("acme-co")

        assert out_path == os.path.join(processed_dir, "acme-co_apify_bronze.v2.csv")
