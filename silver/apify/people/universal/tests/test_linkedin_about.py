from silver.apify.people.universal.datapoints.linkedin_about import extract_linkedin_about


def test_flat_field_name():
    assert extract_linkedin_about({"linkedin_about": "Building at Acme Corp."}) == "Building at Acme Corp."


def test_alternate_field_name():
    assert extract_linkedin_about({"about": "Selling things."}) == "Selling things."


def test_missing_returns_none():
    assert extract_linkedin_about({}) is None
