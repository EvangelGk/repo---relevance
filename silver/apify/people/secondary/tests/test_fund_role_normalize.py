import pytest

from silver.apify.people.secondary.datapoints.fund_role_normalize import function_fund_role_normalize


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("Managing Partner", "MANAGING_PARTNER"),
        ("General Partner", "GENERAL_PARTNER"),
        ("Venture Partner", "VENTURE_PARTNER"),
        ("Operating Partner", "OPERATING_PARTNER"),
        ("Partner", "PARTNER"),
        ("Vice President", "VICE_PRESIDENT"),
        ("VP", "VICE_PRESIDENT"),
        ("Principal", "PRINCIPAL"),
        ("Associate", "ASSOCIATE"),
        ("Analyst", "ANALYST"),
        ("Venture Scout", "SCOUT"),
        ("Random Title", None),
    ],
)
def test_normalize(raw, expected):
    assert function_fund_role_normalize(raw) == expected


def test_specific_alias_wins_over_bare_partner():
    assert function_fund_role_normalize("Managing Partner & Co-Founder") == "MANAGING_PARTNER"
