from silver.people.connector import assemble_person_row


def test_assemble_full_row():
    apify_person = {
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "full_name": "Jane Doe",
        "job_title": "VP of Engineering",
        "seniority": "VP",
        "employed_company": "Acme Corp",
        "country": "United States",
        "linkedin_about": "## About\n\nBuilding at Acme Corp.",
    }
    prospeo_person = {"email": "jane@acme.com", "phone": "+1-555-0100"}

    row = assemble_person_row(apify_person, prospeo_person, source_link="batch-2026-09-08")

    assert row["full_name"] == "Jane Doe"
    assert row["full_name_source"] == "apify"
    assert row["email"] == "jane@acme.com"
    assert row["email_source"] == "prospeo"
    assert row["phone"] == "+1-555-0100"
    assert row["phone_source"] == "prospeo"
    assert row["source_link"] == "batch-2026-09-08"


def test_missing_prospeo_still_tags_email_source():
    row = assemble_person_row({"full_name": "Jane Doe"}, None, None)
    assert row["email"] is None
    assert row["email_source"] == "prospeo"
    assert row["full_name"] == "Jane Doe"


def test_seniority_derived_from_job_title():
    row = assemble_person_row({"job_title": "VP of Engineering"}, None)
    assert row["seniority"] == "VP"
    assert row["seniority_source"] == "apify"


def test_employed_company_derived_from_raw_experience():
    raw_experience = [
        {"title": "Engineer", "company": "OldCo", "start_date": "2018", "end_date": "2020"},
        {"title": "Sr Engineer", "company": "NewCo", "start_date": "2020", "end_date": None},
    ]
    row = assemble_person_row({"full_name": "Jane Doe"}, None, raw_experience=raw_experience)
    assert row["employed_company"] == "NewCo"
    assert row["employed_company_source"] == "apify"


def test_employed_company_falls_back_to_flat_key_without_raw_experience():
    row = assemble_person_row({"full_name": "Jane Doe", "employed_company": "Acme Corp"}, None)
    assert row["employed_company"] == "Acme Corp"
