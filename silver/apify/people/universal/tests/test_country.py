from silver.apify.people.universal.datapoints.country import extract_country


def test_flat_field_name():
    assert extract_country({"country": "United States"}) == "United States"


def test_alternate_field_name():
    assert extract_country({"addressCountryOnly": "Greece"}) == "Greece"


def test_missing_returns_none():
    assert extract_country({}) is None
