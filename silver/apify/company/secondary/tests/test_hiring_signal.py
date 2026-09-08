from silver.apify.company.secondary.datapoints.hiring_signal import function_hiring_signal


def test_actively_hiring():
    assert function_hiring_signal({"open_roles_count": 12}) == "actively_hiring"


def test_hiring_some_roles():
    assert function_hiring_signal({"open_roles_count": 2}) == "hiring"


def test_not_hiring_no_roles_no_growth():
    assert function_hiring_signal({"open_roles_count": 0}) == "not_hiring"


def test_growth_only():
    assert function_hiring_signal({"headcount_growth_pct": 8.5}) == "growing"


def test_shrinking():
    assert function_hiring_signal({"headcount_growth_pct": -3.0}) == "shrinking"


def test_stable():
    assert function_hiring_signal({"headcount_growth_pct": 0.0}) == "stable"


def test_zero_roles_but_growing_prefers_growth():
    assert function_hiring_signal({"open_roles_count": 0, "headcount_growth_pct": 5.0}) == "growing"


def test_nothing_known():
    assert function_hiring_signal({}) is None
    assert function_hiring_signal(None) is None
