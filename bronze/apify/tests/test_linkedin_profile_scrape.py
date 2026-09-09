"""Tests for bronze.apify.linkedin_profile_scrape - mocks run_actor (one
layer below), matching bronze/apify/tests/test_run_actor.py's own
"mock the thing just below what you're testing" convention. No real
network call, no real Apify cost."""
import datetime
import os
from unittest.mock import patch

import pandas as pd
import pytest

from bronze.apify.linkedin_profile_scrape import (
    PROFILE_ACTOR_ID,
    PROFILE_POSTS_ACTOR_ID,
    PROFILE_SCRAPER_MODE_NO_EMAIL,
    RAW_COLUMN,
    SPINE_COLUMNS,
    _months_ago_iso,
    build_person_profile_apify_bronze_rows,
    is_current_at_company,
    person_profile_apify_bronze_filename,
    prospeo_bronze_filename,
    run_apify_person_profile_bronze,
    scrape_linkedin_profile_posts,
    scrape_linkedin_profiles,
)
from bronze.apify._shared import client_processed_dir


def test_dedupes_and_drops_empty_urls_before_calling_the_profile_actor():
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[]) as mock_run:
        scrape_linkedin_profiles(
            ["https://www.linkedin.com/in/acme-person", "", None, "https://www.linkedin.com/in/acme-person"]
        )

    mock_run.assert_called_once_with(
        PROFILE_ACTOR_ID,
        {"profileScraperMode": PROFILE_SCRAPER_MODE_NO_EMAIL, "urls": ["https://www.linkedin.com/in/acme-person"]},
        timeout_seconds=300,
    )


def test_empty_input_skips_the_profile_actor_call_entirely():
    with patch("bronze.apify.linkedin_profile_scrape.run_actor") as mock_run:
        result = scrape_linkedin_profiles([])

    assert result == []
    mock_run.assert_not_called()


def test_dedupes_and_drops_empty_urls_before_calling_the_posts_actor():
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[]) as mock_run:
        scrape_linkedin_profile_posts(
            ["https://www.linkedin.com/in/acme-person", "", None, "https://www.linkedin.com/in/acme-person"]
        )

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == PROFILE_POSTS_ACTOR_ID
    assert args[1]["targetUrls"] == ["https://www.linkedin.com/in/acme-person"]
    assert args[1]["maxPosts"] == 0
    assert kwargs == {"timeout_seconds": 300}


def test_empty_input_skips_the_posts_actor_call_entirely():
    with patch("bronze.apify.linkedin_profile_scrape.run_actor") as mock_run:
        result = scrape_linkedin_profile_posts([])

    assert result == []
    mock_run.assert_not_called()


def test_posts_default_window_is_six_months_via_posted_limit_date():
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[]) as mock_run:
        scrape_linkedin_profile_posts(["https://www.linkedin.com/in/acme-person"])

    sent_cutoff = mock_run.call_args[0][1]["postedLimitDate"]
    assert sent_cutoff == _months_ago_iso(6)


def test_max_posts_override_is_passed_through():
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[]) as mock_run:
        scrape_linkedin_profile_posts(["https://www.linkedin.com/in/acme-person"], max_posts=50)

    assert mock_run.call_args[0][1]["maxPosts"] == 50


def test_months_ago_iso_uses_real_calendar_month_arithmetic_not_a_30_day_approximation():
    # 2026-08-31 minus 6 months -> 2026-02-28 (Feb has no 31st, not day-count math).
    assert _months_ago_iso(6, today=datetime.date(2026, 8, 31)) == "2026-02-28"
    # Crossing a year boundary.
    assert _months_ago_iso(6, today=datetime.date(2026, 3, 15)) == "2025-09-15"
    assert _months_ago_iso(0, today=datetime.date(2026, 3, 15)) == "2026-03-15"


def _spine_df(**overrides):
    defaults = {
        "clay_profile_id": ["1"],
        "name": ["Ada Lovelace"],
        "linkedin_url": ["https://www.linkedin.com/in/ada"],
    }
    defaults.update(overrides)
    return pd.DataFrame(defaults)


def test_bronze_row_joins_on_original_query_url_not_linkedin_url():
    """Regression test: the actor's own `linkedinUrl` output can be a
    LinkedIn-renamed/redirected URL, not the one that was requested -
    joining on it silently dropped rows in the first live run (see the
    module docstring). `originalQuery.url` is the reliable key."""
    spine = _spine_df()
    raw_item = {
        "originalQuery": {"url": "https://www.linkedin.com/in/ada"},
        "linkedinUrl": "https://www.linkedin.com/in/ada-lovelace-renamed",
        "followerCount": 500,
    }
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[raw_item]):
        out = build_person_profile_apify_bronze_rows(spine)

    assert out.loc[0, RAW_COLUMN] == raw_item


def test_bronze_row_output_columns_are_exactly_the_identity_spine_plus_json():
    spine = _spine_df()
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[]):
        out = build_person_profile_apify_bronze_rows(spine)

    assert list(out.columns) == SPINE_COLUMNS + [RAW_COLUMN]


def test_a_row_with_no_linkedin_url_still_produces_a_row():
    spine = _spine_df(linkedin_url=[None])
    with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[]) as mock_run:
        out = build_person_profile_apify_bronze_rows(spine)

    mock_run.assert_not_called()
    assert len(out) == 1
    assert pd.isna(out.loc[0, RAW_COLUMN])


def test_bronze_row_missing_spine_column_raises_clearly():
    spine = _spine_df().drop(columns=["name"])
    with pytest.raises(ValueError, match="name"):
        build_person_profile_apify_bronze_rows(spine)


def test_filenames_are_prefixed_with_the_client_id():
    assert prospeo_bronze_filename("acme-co") == "acme-co_prospeo_bronze.csv"
    assert person_profile_apify_bronze_filename("acme-co") == "acme-co_person_profile_apify_bronze.csv"


def test_run_apify_person_profile_bronze_reads_prospeo_bronze_and_writes_person_profile_apify_bronze(tmp_path):
    with patch("bronze.apify._shared._REPO_ROOT", str(tmp_path)):
        processed_dir = client_processed_dir("acme-co")
        os.makedirs(processed_dir, exist_ok=True)
        _spine_df(matched_company=["Acme"]).to_csv(
            os.path.join(processed_dir, "acme-co_prospeo_bronze.csv"), index=False
        )

        raw_item = {"originalQuery": {"url": "https://www.linkedin.com/in/ada"}, "followerCount": 500}
        with patch("bronze.apify.linkedin_profile_scrape.run_actor", return_value=[raw_item]):
            out_path = run_apify_person_profile_bronze("acme-co")

        assert out_path == os.path.join(processed_dir, "acme-co_person_profile_apify_bronze.csv")
        result = pd.read_csv(out_path)
        assert list(result.columns) == SPINE_COLUMNS + [RAW_COLUMN]
        assert "followerCount" in result.loc[0, RAW_COLUMN]


def test_run_apify_person_profile_bronze_raises_clearly_if_prospeo_bronze_is_missing(tmp_path):
    with patch("bronze.apify._shared._REPO_ROOT", str(tmp_path)):
        with pytest.raises(FileNotFoundError, match="acme-co_prospeo_bronze.csv"):
            run_apify_person_profile_bronze("acme-co")


# --- is_current_at_company ---

_CURRENT_ROLE = {
    "companyName": "Acme Corp",
    "companyLinkedinUrl": "https://www.linkedin.com/company/acme/",
    "endDate": {"text": "Present"},
}
_PAST_ROLE = {
    "companyName": "Beta Inc",
    "companyLinkedinUrl": "https://www.linkedin.com/company/beta/",
    "endDate": {"month": "Jan", "year": 2022, "text": "Jan 2022"},
}


def test_is_current_at_company_true_when_matched_role_has_no_end_date():
    profile = {"experience": [_PAST_ROLE, _CURRENT_ROLE]}
    assert is_current_at_company(profile, company_name="Acme Corp") is True


def test_is_current_at_company_matches_by_linkedin_url_trailing_slash_normalized():
    profile = {"experience": [_CURRENT_ROLE]}
    assert is_current_at_company(profile, company_linkedin_url="https://www.linkedin.com/company/acme") is True


def test_is_current_at_company_false_when_matched_role_has_ended():
    profile = {"experience": [_PAST_ROLE]}
    assert is_current_at_company(profile, company_name="Beta Inc") is False


def test_is_current_at_company_none_when_no_experience_entry_matches():
    profile = {"experience": [_PAST_ROLE, _CURRENT_ROLE]}
    assert is_current_at_company(profile, company_name="Nonexistent Co") is None


def test_is_current_at_company_none_when_profile_is_missing():
    assert is_current_at_company(None, company_name="Acme Corp") is None


def test_is_current_at_company_requires_at_least_one_identifier():
    with pytest.raises(ValueError):
        is_current_at_company({"experience": []})


def test_is_current_at_company_name_match_is_case_insensitive_and_whitespace_trimmed():
    profile = {"experience": [_CURRENT_ROLE]}
    assert is_current_at_company(profile, company_name="  acme corp  ") is True
