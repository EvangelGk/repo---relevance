"""Tests for client_context.schema - the load/validate path a client
context JSON file goes through before anything (bronze/clay's query
builder today) trusts it."""
import json
from pathlib import Path

import pytest

from client_context.schema import (
    ClientContext,
    ClientContextError,
    list_client_contexts,
    load_client_context,
)

EXAMPLE_PATH = Path(__file__).parent.parent / "clients" / "example_client.json"


def test_loads_the_committed_example_client():
    context = load_client_context(str(EXAMPLE_PATH))
    assert isinstance(context, ClientContext)
    assert context.client_id == "example-client"
    assert context.industries == ("Software Development", "Technology, Information and Internet")
    assert context.company_size_buckets == ("51-200", "201-500")
    assert context.limit == 100


def test_missing_required_field_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "Missing client_id"}), encoding="utf-8")
    with pytest.raises(ClientContextError, match="client_id: required but missing"):
        load_client_context(str(path))


def test_unknown_industry_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps({"client_id": "x", "name": "X", "industries": ["Not A Real Industry"]}),
        encoding="utf-8",
    )
    with pytest.raises(ClientContextError, match="industries.*Not A Real Industry"):
        load_client_context(str(path))


def test_unknown_company_size_bucket_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps({"client_id": "x", "name": "X", "company_size_buckets": ["huge"]}),
        encoding="utf-8",
    )
    with pytest.raises(ClientContextError, match="company_size_buckets"):
        load_client_context(str(path))


def test_non_positive_limit_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"client_id": "x", "name": "X", "limit": 0}), encoding="utf-8")
    with pytest.raises(ClientContextError, match="limit"):
        load_client_context(str(path))


def test_defaults_fill_in_when_optional_fields_are_absent(tmp_path):
    path = tmp_path / "minimal.json"
    path.write_text(json.dumps({"client_id": "x", "name": "X"}), encoding="utf-8")
    context = load_client_context(str(path))
    assert context.industries == ()
    assert context.exclude_domains == ()
    assert context.limit == 100
    assert context.notes is None


def test_list_client_contexts_on_missing_directory_returns_empty(tmp_path):
    assert list_client_contexts(str(tmp_path / "does_not_exist")) == []


def test_list_client_contexts_loads_and_sorts_by_filename(tmp_path):
    (tmp_path / "b_client.json").write_text(
        json.dumps({"client_id": "b", "name": "B"}), encoding="utf-8"
    )
    (tmp_path / "a_client.json").write_text(
        json.dumps({"client_id": "a", "name": "A"}), encoding="utf-8"
    )
    (tmp_path / "not_a_client.txt").write_text("ignored", encoding="utf-8")

    contexts = list_client_contexts(str(tmp_path))
    assert [c.client_id for c in contexts] == ["a", "b"]


def test_list_client_contexts_raises_on_first_invalid_file(tmp_path):
    (tmp_path / "a_bad.json").write_text(json.dumps({"name": "No id"}), encoding="utf-8")
    with pytest.raises(ClientContextError):
        list_client_contexts(str(tmp_path))
