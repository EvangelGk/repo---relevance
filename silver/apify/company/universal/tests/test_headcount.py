from silver.apify.company.universal.datapoints.headcount import extract_headcount


def test_flat_field_name():
    assert extract_headcount({"headcount": 340}) == 340


def test_alternate_field_name():
    assert extract_headcount({"employeeCount": 50}) == 50


def test_missing_returns_none():
    assert extract_headcount({}) is None
