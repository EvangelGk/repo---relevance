from silver.apify.people.universal.datapoints.company_industry import extract_company_industry


def test_flat_field_name():
    assert extract_company_industry({"company_industry": "Fintech"}) == "Fintech"


def test_alternate_field_name():
    assert extract_company_industry({"companyIndustry": "Logistics Software"}) == "Logistics Software"


def test_another_alternate_field_name():
    assert extract_company_industry({"currentCompanyIndustry": "Healthcare"}) == "Healthcare"


def test_missing_returns_none():
    assert extract_company_industry({}) is None
