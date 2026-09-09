from silver.apify.people.universal.datapoints.age import extract_age


def test_flat_field_name():
    assert extract_age({"age": 34}) == 34


def test_alternate_field_name():
    assert extract_age({"estimatedAge": 41}) == 41


def test_missing_returns_none():
    assert extract_age({}) is None
