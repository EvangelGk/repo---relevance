from silver.company.connector import assemble_company_row
from silver.firecrawl.firecrawl import Firecrawl

_SAMPLE_MARKDOWN = """
# Acme Corp

Acme Corp builds rocket-powered logistics software for enterprise supply
chains, helping teams ship faster without sacrificing reliability.

© 2024 Acme Corp. All rights reserved.
"""


def test_assemble_from_live_firecrawl_output():
    firecrawl = Firecrawl()
    result = firecrawl.run_all(_SAMPLE_MARKDOWN, source_url="https://acme.example.com/about")
    firecrawl_row = result["row"]

    apify_company = {
        "name": "Acme Corp",
        "industry": "Logistics Software",
        "headcount": 340,
        "location": "Austin, TX",
        "linkedin_url": "https://linkedin.com/company/acme-corp",
    }

    row = assemble_company_row(apify_company, firecrawl_row, source_link="batch-2026-09-08")

    assert row["name"] == "Acme Corp"
    assert row["name_source"] == "apify"
    assert row["industry"] == "Logistics Software"
    assert row["headcount"] == 340
    assert row["location"] == "Austin, TX"
    assert row["location_source"] == "apify"
    assert row["linkedin_url"] == "https://linkedin.com/company/acme-corp"
    assert row["domain"] == "acme.example.com"
    assert row["domain_source"] == "firecrawl"
    assert row["description"]
    assert row["description_source"] == "firecrawl"
    assert row["company_id"] is not None
    assert row["source_link"] == "batch-2026-09-08"


def test_missing_inputs_dont_crash():
    row = assemble_company_row(None, None, None)
    assert row["name"] is None
    assert row["name_source"] == "apify"
    assert row["domain"] is None
    assert row["source_link"] is None
