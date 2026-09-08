from silver.apify.people.universal.datapoints.job_title import extract_job_title


def test_flat_field_name():
    assert extract_job_title({"job_title": "VP of Engineering"}) == "VP of Engineering"


def test_alternate_field_name():
    assert extract_job_title({"headline": "Director of Sales"}) == "Director of Sales"


def test_missing_returns_none():
    assert extract_job_title({}) is None
