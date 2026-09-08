from silver.apify.company.universal.datapoints.linkedin_url import extract_linkedin_url


def test_flat_field_name():
    assert extract_linkedin_url({"linkedin_url": "https://linkedin.com/company/acme-corp"}) == "https://linkedin.com/company/acme-corp"


def test_alternate_field_name():
    assert extract_linkedin_url({"linkedinUrl": "https://linkedin.com/company/beta-inc"}) == "https://linkedin.com/company/beta-inc"


def test_missing_returns_none():
    assert extract_linkedin_url({}) is None
