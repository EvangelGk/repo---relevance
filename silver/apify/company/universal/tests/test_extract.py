from silver.apify.company.universal.extract import extract_company_universal_fields


def test_flat_field_names():
    raw = {
        "name": "Acme Corp",
        "industry": "Logistics Software",
        "headcount": 340,
        "location": "Austin, TX",
        "linkedin_url": "https://linkedin.com/company/acme-corp",
    }
    out = extract_company_universal_fields(raw)
    assert out == {
        "name": "Acme Corp",
        "industry": "Logistics Software",
        "headcount": 340,
        "location": "Austin, TX",
        "linkedin_url": "https://linkedin.com/company/acme-corp",
    }


def test_alternate_field_names_and_nested_headquarter():
    raw = {
        "companyName": "Beta Inc",
        "companyIndustry": "Fintech",
        "employeeCount": 50,
        "headquarter": {"city": "Athens", "geographicArea": "Attica", "country": "Greece"},
        "linkedinUrl": "https://linkedin.com/company/beta-inc",
    }
    out = extract_company_universal_fields(raw)
    assert out["name"] == "Beta Inc"
    assert out["industry"] == "Fintech"
    assert out["headcount"] == 50
    assert out["location"] == "Athens, Attica, Greece"
    assert out["linkedin_url"] == "https://linkedin.com/company/beta-inc"


def test_missing_input_returns_all_none():
    out = extract_company_universal_fields(None)
    assert all(v is None for v in out.values())
