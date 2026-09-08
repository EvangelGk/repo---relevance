import pytest

from silver.apify.people.secondary.datapoints.connections_band import function_connections_band


@pytest.mark.parametrize(
    "count,expected",
    [(None, None), (0, "0"), (137, "137"), (499, "499"), (500, "500+"), (2000, "500+")],
)
def test_band(count, expected):
    assert function_connections_band(count) == expected


def test_negative_raises():
    with pytest.raises(ValueError):
        function_connections_band(-1)
