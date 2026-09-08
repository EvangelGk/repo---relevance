from silver.apify.people.universal.datapoints.full_name import extract_full_name


def test_flat_field_name():
    assert extract_full_name({"full_name": "Jane Doe"}) == "Jane Doe"


def test_split_name_fallback():
    assert extract_full_name({"firstName": "John", "lastName": "Doe"}) == "John Doe"


def test_missing_returns_none():
    assert extract_full_name({}) is None
