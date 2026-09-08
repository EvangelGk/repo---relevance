from silver.apify.company.universal.datapoints.name import extract_name


def test_flat_field_name():
    assert extract_name({"name": "Acme Corp"}) == "Acme Corp"


def test_alternate_field_name():
    assert extract_name({"companyName": "Beta Inc"}) == "Beta Inc"


def test_missing_returns_none():
    assert extract_name({}) is None
    assert extract_name(None) is None
