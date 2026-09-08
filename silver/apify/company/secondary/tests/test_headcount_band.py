import pytest

from silver.apify.company.secondary.datapoints.headcount_band import function_headcount_band


@pytest.mark.parametrize(
    "headcount,expected",
    [
        (None, None),
        (0, "1-10"),
        (10, "1-10"),
        (11, "11-50"),
        (200, "51-200"),
        (500, "201-500"),
        (1000, "501-1000"),
        (5000, "1001-5000"),
        (10000, "5001-10000"),
        (10001, "10001+"),
        (50000, "10001+"),
    ],
)
def test_bands(headcount, expected):
    assert function_headcount_band(headcount) == expected


def test_negative_raises():
    with pytest.raises(ValueError):
        function_headcount_band(-5)
