from silver.apify.company.universal.datapoints.location import extract_location


def test_flat_field_name():
    assert extract_location({"location": "Austin, TX"}) == "Austin, TX"


def test_nested_headquarter_object():
    raw = {"headquarter": {"city": "Athens", "geographicArea": "Attica", "country": "Greece"}}
    assert extract_location(raw) == "Athens, Attica, Greece"


def test_missing_returns_none():
    assert extract_location({}) is None
