from silver.apify.people.universal.datapoints.linkedin_url import extract_linkedin_url


def test_flat_field_name():
    assert extract_linkedin_url({"linkedin_url": "https://linkedin.com/in/janedoe"}) == "https://linkedin.com/in/janedoe"


def test_alternate_field_name():
    assert extract_linkedin_url({"linkedinUrl": "https://linkedin.com/in/johndoe"}) == "https://linkedin.com/in/johndoe"


def test_missing_returns_none():
    assert extract_linkedin_url({}) is None
