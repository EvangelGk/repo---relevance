from silver.apify.people.universal.extract import extract_person_universal_fields


def test_flat_field_names():
    raw = {
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "full_name": "Jane Doe",
        "job_title": "VP of Engineering",
        "country": "United States",
        "linkedin_about": "Building at Acme Corp.",
        "age": 34,
        "company_industry": "Fintech",
    }
    out = extract_person_universal_fields(raw)
    assert out["linkedin_url"] == raw["linkedin_url"]
    assert out["full_name"] == raw["full_name"]
    assert out["job_title"] == raw["job_title"]
    assert out["country"] == raw["country"]
    assert out["linkedin_about"] == raw["linkedin_about"]
    assert out["age"] == 34
    assert out["company_industry"] == "Fintech"
    assert out["seniority"] == "VP"


def test_alternate_field_names_and_split_name():
    raw = {
        "linkedinUrl": "https://linkedin.com/in/johndoe",
        "firstName": "John",
        "lastName": "Doe",
        "headline": "Director of Sales",
        "addressCountryOnly": "Greece",
        "about": "Selling things.",
        "estimatedAge": 41,
        "companyIndustry": "Logistics Software",
    }
    out = extract_person_universal_fields(raw)
    assert out["linkedin_url"] == "https://linkedin.com/in/johndoe"
    assert out["full_name"] == "John Doe"
    assert out["job_title"] == "Director of Sales"
    assert out["seniority"] == "DIRECTOR"
    assert out["country"] == "Greece"
    assert out["linkedin_about"] == "Selling things."
    assert out["age"] == 41
    assert out["company_industry"] == "Logistics Software"


def test_missing_input_returns_all_none():
    out = extract_person_universal_fields(None)
    assert all(v is None for v in out.values())
