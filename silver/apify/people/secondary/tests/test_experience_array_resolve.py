from datetime import date

from silver.apify.people.secondary.datapoints.experience_array_resolve import function_experience_array_resolve


def test_empty():
    result = function_experience_array_resolve(None)
    assert result == {"experiences": [], "total_years_experience": None, "current_tenure_years": None}


def test_single_ongoing_role():
    raw = [{"title": "Engineer", "company": "Acme", "start_date": "Jan 2020", "end_date": None}]
    result = function_experience_array_resolve(raw, today=date(2026, 1, 1))
    assert result["total_years_experience"] == 6.0
    assert result["current_tenure_years"] == 6.0
    assert result["experiences"][0]["is_current"] is True


def test_two_sequential_roles():
    raw = [
        {"title": "Analyst", "company": "Acme", "start_date": "2018-01", "end_date": "2020-01"},
        {"title": "Manager", "company": "Acme", "start_date": "2020-01", "end_date": "Present"},
    ]
    result = function_experience_array_resolve(raw, today=date(2023, 1, 1))
    assert result["total_years_experience"] == 5.0
    assert result["current_tenure_years"] == 3.0


def test_unparseable_dates_are_skipped_not_fatal():
    raw = [{"title": "Mystery", "company": "?", "start_date": "sometime", "end_date": None}]
    result = function_experience_array_resolve(raw, today=date(2026, 1, 1))
    assert result["experiences"][0]["duration_years"] is None
    assert result["total_years_experience"] is None
