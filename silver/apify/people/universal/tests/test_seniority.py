from silver.apify.people.universal.datapoints.seniority import function_seniority


def test_c_level():
    assert function_seniority("Chief Executive Officer") == "C_LEVEL"
    assert function_seniority("Co-Founder & CEO") == "C_LEVEL"


def test_vp():
    assert function_seniority("VP of Engineering") == "VP"


def test_director():
    assert function_seniority("Director of Sales") == "DIRECTOR"
    assert function_seniority("Head of Growth") == "DIRECTOR"


def test_manager():
    assert function_seniority("Engineering Manager") == "MANAGER"


def test_ic_fallback():
    assert function_seniority("Software Engineer") == "IC"


def test_none_and_empty():
    assert function_seniority(None) is None
    assert function_seniority("") is None
    assert function_seniority("   ") is None
