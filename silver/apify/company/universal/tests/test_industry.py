from silver.apify.company.universal.datapoints.industry import extract_industry


def test_flat_field_name():
    assert extract_industry({"industry": "Logistics Software"}) == "Logistics Software"


def test_alternate_field_name():
    assert extract_industry({"companyIndustry": "Fintech"}) == "Fintech"


def test_missing_returns_none():
    assert extract_industry({}) is None
