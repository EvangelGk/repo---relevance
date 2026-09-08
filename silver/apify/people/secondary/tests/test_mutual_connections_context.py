from silver.apify.people.secondary.datapoints.mutual_connections_context import function_mutual_connections_context


def test_none():
    assert function_mutual_connections_context(None) == {"mutual_count": 0, "sample_names": []}


def test_int_count():
    assert function_mutual_connections_context(12) == {"mutual_count": 12, "sample_names": []}


def test_list_of_dicts_caps_sample_at_three():
    connections = [{"name": n} for n in ["John", "Priya", "Wei", "Ana", "Sam"]]
    result = function_mutual_connections_context(connections)
    assert result["mutual_count"] == 5
    assert result["sample_names"] == ["John", "Priya", "Wei"]
