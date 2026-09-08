import json

from silver.apify.people.universal.loader import load_apify_person_records


def test_bare_array():
    raw = [{"full_name": "Jane Doe"}, {"full_name": "John Doe"}]
    assert load_apify_person_records(raw) == raw


def test_items_wrapper():
    raw = {"items": [{"full_name": "Jane Doe"}]}
    assert load_apify_person_records(raw) == [{"full_name": "Jane Doe"}]


def test_reads_from_file(tmp_path):
    raw = [{"full_name": "Jane Doe"}]
    path = tmp_path / "apify_people.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_apify_person_records(path) == raw
