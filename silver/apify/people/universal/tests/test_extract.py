from silver.apify.people.universal.extract import extract_person_universal_fields


def test_flat_field_names():
    raw = {
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "full_name": "Jane Doe",
        "job_title": "VP of Engineering",
        "country": "United States",
        "linkedin_about": "Building at Acme Corp.",
    }
    out = extract_person_universal_fields(raw)
    assert out == raw


def test_alternate_field_names_and_split_name():
    raw = {
        "linkedinUrl": "https://linkedin.com/in/johndoe",
        "firstName": "John",
        "lastName": "Doe",
        "headline": "Director of Sales",
        "addressCountryOnly": "Greece",
        "about": "Selling things.",
    }
    out = extract_person_universal_fields(raw)
    assert out["linkedin_url"] == "https://linkedin.com/in/johndoe"
    assert out["full_name"] == "John Doe"
    assert out["job_title"] == "Director of Sales"
    assert out["country"] == "Greece"
    assert out["linkedin_about"] == "Selling things."


def test_missing_input_returns_all_none():
    out = extract_person_universal_fields(None)
    assert all(v is None for v in out.values())
