import json

import pytest

from silver.apify.company.universal.loader import load_apify_company_records


def test_bare_array():
    raw = [{"name": "Acme Corp"}, {"name": "Beta Inc"}]
    assert load_apify_company_records(raw) == raw


def test_items_wrapper():
    raw = {"items": [{"name": "Acme Corp"}]}
    assert load_apify_company_records(raw) == [{"name": "Acme Corp"}]


def test_single_record_dict_without_items_or_data():
    raw = {"name": "Acme Corp"}
    assert load_apify_company_records(raw) == [{"name": "Acme Corp"}]


def test_reads_from_file(tmp_path):
    raw = [{"name": "Acme Corp"}]
    path = tmp_path / "apify_companies.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_apify_company_records(path) == raw


def test_invalid_shape_raises():
    with pytest.raises(ValueError):
        load_apify_company_records(42)
