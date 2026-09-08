import pytest

from silver.apify.company.secondary.datapoints.company_type_normalize import function_company_type_normalize


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("Public Company", "PUBLIC_COMPANY"),
        ("Privately Held", "PRIVATELY_HELD"),
        ("Private Company", "PRIVATELY_HELD"),
        ("Nonprofit", "NONPROFIT"),
        ("Non-Profit", "NONPROFIT"),
        ("Government Agency", "GOVERNMENT_AGENCY"),
        ("Partnership", "PARTNERSHIP"),
        ("Self-Employed", "SELF_EMPLOYED"),
        ("Sole Proprietorship", "SOLE_PROPRIETORSHIP"),
        ("Educational Institution", "EDUCATIONAL_INSTITUTION"),
        ("Some Unrecognized Value", None),
    ],
)
def test_normalize(raw, expected):
    assert function_company_type_normalize(raw) == expected
