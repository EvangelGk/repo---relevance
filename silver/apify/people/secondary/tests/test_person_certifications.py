from silver.apify.people.secondary.datapoints.person_certifications import function_person_certifications


def test_none_returns_empty():
    assert function_person_certifications(None) == []


def test_normalizes_varied_key_names():
    raw = [
        {"name": "AWS Certified Solutions Architect", "issuer": "Amazon", "issued_date": "2022-05"},
        {"title": "PMP", "authority": "PMI", "date": "2019"},
        {"certification": "CFA Level 1", "organization": "CFA Institute"},
    ]
    result = function_person_certifications(raw)
    assert result == [
        {"name": "AWS Certified Solutions Architect", "issuer": "Amazon", "issued_date": "2022-05"},
        {"name": "PMP", "issuer": "PMI", "issued_date": "2019"},
        {"name": "CFA Level 1", "issuer": "CFA Institute", "issued_date": None},
    ]


def test_entries_without_name_are_dropped():
    raw = [{"issuer": "Nobody knows what this is"}]
    assert function_person_certifications(raw) == []
