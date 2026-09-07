"""Smoke test for the firecrawl package, driven by the fixtures in this
directory: sample_input.md (a markdown company profile) and
sample_context.json (context overrides for that same profile).

sample_input.html and the raw-HTML-specific test that used it were removed
2026-09-08 along with structured_data_extract and site_locale_detect's
hreflang path - both needed a <script>/<html lang> attribute that cleaned
markdown never actually preserves, so they were structurally dead against
real input.

Firecrawl.run_all() returns {"row": {...}, "function_report": {...}} - these
tests read out of "row" for datapoint values, same shape as before minus the
relevance gate (is_company_profile moved to
silver_orchestrator.orchestrator.SilverOrchestrator - see
silver/silver_orchestrator/tests/test_silver_orchestrator.py for that).
"""
import json
import re
from pathlib import Path

from silver.firecrawl import Firecrawl

FIXTURES_DIR = Path(__file__).parent
SAMPLE_MD = (FIXTURES_DIR / "sample_input.md").read_text(encoding="utf-8")
SAMPLE_CONTEXT = json.loads((FIXTURES_DIR / "sample_context.json").read_text(encoding="utf-8"))


def _decode_cells(row: dict):
    """Yield (column, decoded_value) for every cell, JSON-decoding any cell
    that looks like a JSON object/array so dict-shaped results can be
    inspected the same way whether they came back as a dict or a
    run_all_as_dataframe()-flattened JSON string."""
    for column, value in row.items():
        if isinstance(value, str) and value[:1] in "{[":
            try:
                yield column, json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        yield column, value


def test_domain_normalize_requires_context_source_url():
    # No context["source_url"] given, and the only link in SAMPLE_MD is a
    # LinkedIn footer link - domain_normalize must NOT guess "linkedin.com"
    # from it (that used to be the buggy fallback behavior). It should
    # come back None rather than confidently mislabel the row.
    result = Firecrawl().run_all(SAMPLE_MD)
    assert result["row"]["domain_normalize"] is None
    assert result["function_report"]["domain_normalize"]["source"] is None


def test_domain_normalize_uses_context_source_url():
    result = Firecrawl().run_all(SAMPLE_MD, source_url="https://app.acme.com/pricing?utm_source=x")
    assert result["row"]["domain_normalize"] == "acme.com"
    assert result["function_report"]["domain_normalize"]["source"] == "context"


def test_date_normalize_finds_iso_date():
    row = Firecrawl().run_all(SAMPLE_MD)["row"]
    assert row["date_normalize"]
    assert "2019-03-03" in row["date_normalize"]


def test_company_entity_resolve_infers_parent_guess_from_prose():
    result = Firecrawl().run_all(SAMPLE_MD)
    row = result["row"]
    assert row["company_entity_resolve"]["parent_guess"] == "Acme Holdings GmbH"
    assert row["company_entity_resolve"]["source"] == "markdown"
    assert result["function_report"]["company_entity_resolve"]["source"] == "markdown"


def test_site_locale_detect_finds_all_three_languages():
    row = Firecrawl().run_all(SAMPLE_MD)["row"]
    assert set(row["site_locale_detect"]) >= {"en", "de", "fr"}


def test_tech_stack_normalize_separates_mentions_from_detected():
    row = Firecrawl().run_all(SAMPLE_MD)["row"]
    mentioned_ids = {entry["tool_id"] for entry in row["tech_stack_normalize"]["mentioned_technologies"]}
    assert "segment" in mentioned_ids
    assert row["tech_stack_normalize"]["detected_stack"] == []


def test_tech_stack_normalize_detected_stack_from_context():
    result = Firecrawl().run_all(SAMPLE_MD, **SAMPLE_CONTEXT)
    row = result["row"]
    detected_ids = {entry["tool_id"] for entry in row["tech_stack_normalize"]["detected_stack"]}
    assert {"hubspot", "google_analytics", "segment"} <= detected_ids
    assert result["function_report"]["tech_stack_normalize"]["source"] == "context"


def test_tech_stack_normalize_broadened_catalog_finds_new_vendors():
    # Vendors added in the 2026-09-08 catalog expansion - none of these 18
    # were recognized before that change.
    snippet = (
        "We run our support desk on Front App, deploy on Vercel, and use "
        "Snowflake plus dbt labs for our data warehouse. Engineering tracks "
        "work in Linear.app and pays the team through Gusto.com."
    )
    row = Firecrawl().run_all(snippet)["row"]
    mentioned_ids = {entry["tool_id"] for entry in row["tech_stack_normalize"]["mentioned_technologies"]}
    assert {"frontapp", "vercel", "snowflake", "dbt", "linear_app", "gusto"} <= mentioned_ids


def test_careers_page_parse_returns_five_rows():
    row = Firecrawl().run_all(SAMPLE_MD)["row"]
    assert len(row["careers_page_parse"]) == 5


def test_careers_page_parse_strict_format_fields_are_not_shifted():
    # Regression test for a real bug found 2026-09-08 by inspecting actual
    # output (not just a count): matching the strict format as one findall()
    # over the whole section let a role line's leading "- " bullet get
    # mistaken for a field separator, shifting every field over by one and
    # splicing the "## Careers" heading in as a bogus first "role."
    row = Firecrawl().run_all(SAMPLE_MD)["row"]
    roles = row["careers_page_parse"]
    assert roles[0] == {
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "Berlin, Germany",
        "posted_date": "2024-01-15",
    }
    assert all(role["title"] != "## Careers" for role in roles)


def test_careers_page_parse_loose_fallback_on_realistic_formatting():
    # Real scraped careers pages essentially never match the strict
    # "TITLE — DEPT — LOCATION — Posted YYYY-MM-DD" format - this is the
    # shape a real page is much more likely to actually produce.
    snippet = (
        "## Open Positions\n\n"
        "- **Senior Backend Engineer** (Berlin, Germany)\n"
        "- Product Designer - Design (Remote)\n"
        "- Account Executive\n"
    )
    result = Firecrawl().run_all(snippet)
    roles = result["row"]["careers_page_parse"]
    assert len(roles) == 3
    assert roles[0] == {
        "title": "Senior Backend Engineer",
        "department": None,
        "location": "Berlin, Germany",
        "posted_date": None,
    }
    assert roles[1] == {
        "title": "Product Designer",
        "department": "Design",
        "location": "Remote",
        "posted_date": None,
    }
    assert roles[2] == {
        "title": "Account Executive",
        "department": None,
        "location": None,
        "posted_date": None,
    }
    assert result["function_report"]["careers_page_parse"]["source"] == "markdown"


def test_careers_page_parse_empty_without_a_careers_heading():
    # A bullet list that happens to exist on a non-careers page should not
    # be misread as job postings - the loose parser only runs inside a
    # careers-shaped section.
    snippet = "## Features\n\n- Real-time analytics dashboard\n- Single sign-on\n"
    result = Firecrawl().run_all(snippet)
    assert result["row"]["careers_page_parse"] == []
    assert result["function_report"]["careers_page_parse"]["source"] is None


def test_social_links_extract_recovers_bare_urls_when_brackets_are_stripped():
    # Flatten "[LinkedIn](https://...)" markdown-link syntax down to a bare
    # URL, as if link brackets were stripped before this function saw the
    # text - the primary bracket-link regex will find nothing, so the bare
    # URL fallback has to do the classifying.
    flattened = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r"\2", SAMPLE_MD)
    assert "[LinkedIn]" not in flattened

    row = Firecrawl().run_all(flattened)["row"]
    assert row["social_links_extract"] is not None
    assert "linkedin.com" in row["social_links_extract"]["linkedin_url"]


def test_run_all_as_dataframe_never_all_null_dict():
    sparse_snippet = "Just a plain paragraph with no links, prices, or other extractable signals at all."
    df = Firecrawl().run_all_as_dataframe(sparse_snippet)
    row = df.iloc[0].to_dict()

    for column, decoded in _decode_cells(row):
        if isinstance(decoded, dict) and decoded:
            assert not all(v is None for v in decoded.values()), f"{column} is an all-null dict: {decoded}"

    # social_links_extract found zero links on this snippet - it should
    # collapse to a plain None, not a 6-key dict of nulls.
    assert row["social_links_extract"] is None or (row["social_links_extract"] != row["social_links_extract"])


def test_experience_signal_extract_explicit_founding_year():
    row = Firecrawl().run_all("Acme Corp. Founded in 2015, we help teams close more deals.")["row"]
    signal = row["experience_signal_extract"]
    assert signal["founding_year"] == 2015
    assert signal["founding_year_source"] == "explicit"


def test_experience_signal_extract_derives_founding_year_from_duration():
    row = Firecrawl().run_all(
        "Acme Corp has over 30 years of experience serving the logistics industry.",
        current_year=2025,
    )["row"]
    signal = row["experience_signal_extract"]
    assert signal["founding_year_source"] == "derived"
    assert signal["years_in_business_claim"] == 30
    assert signal["founding_year"] == 2025 - 30


def test_service_region_extract_finds_multiple_us_states():
    row = Firecrawl().run_all("We have engineering teams in Texas and customer success in California.")["row"]
    assert len(row["service_region_extract"]) >= 2
    assert "Texas" in row["service_region_extract"]
    assert "California" in row["service_region_extract"]


def test_function_report_covers_all_datapoint_functions_and_excludes_conflict_check():
    result = Firecrawl().run_all(SAMPLE_MD, **SAMPLE_CONTEXT)
    report = result["function_report"]
    # 17 original + company_description_extract, minus structured_data_extract,
    # regulatory_event_classify, timeseries_snapshot, freshness (removed 2026-09-08).
    assert len(report) == 14
    assert "conflict_check" not in report
    for name, entry in report.items():
        assert set(entry) == {"ran", "is_empty", "source"}
        assert entry["ran"] is True


def test_function_report_flags_empty_functions_with_no_source():
    sparse_snippet = "Just a plain paragraph with no links, prices, or other extractable signals at all."
    report = Firecrawl().run_all(sparse_snippet)["function_report"]
    assert report["pricing_locale_extract"]["is_empty"] is True
    assert report["pricing_locale_extract"]["source"] is None


def test_company_description_extract_uses_first_substantive_paragraph():
    result = Firecrawl().run_all(SAMPLE_MD)
    row = result["row"]
    assert row["company_description_extract"] == (
        "Acme Corp is a subsidiary of Acme Holdings GmbH. Acme Corp is a "
        "cloud-based SaaS platform for revenue teams headquartered in Berlin, Germany."
    )
    assert result["function_report"]["company_description_extract"]["source"] == "markdown"


def test_company_description_extract_prefers_context_override():
    result = Firecrawl().run_all(SAMPLE_MD, company_description="Override description from Apify.")
    row = result["row"]
    assert row["company_description_extract"] == "Override description from Apify."
    assert result["function_report"]["company_description_extract"]["source"] == "context"


def test_company_description_extract_empty_when_no_substantive_prose():
    heading_only_snippet = "# Acme\n\nHi.\n"
    result = Firecrawl().run_all(heading_only_snippet)
    assert result["row"]["company_description_extract"] is None
    assert result["function_report"]["company_description_extract"]["source"] is None
