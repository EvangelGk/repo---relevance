import json

from silver.firecrawl.raw_response_loader import extract_markdown_and_source_url


def test_flat_shape():
    raw = {"markdown": "# Acme Corp", "metadata": {"sourceURL": "https://acme.example.com"}}
    out = extract_markdown_and_source_url(raw)
    assert out == {"markdown": "# Acme Corp", "source_url": "https://acme.example.com"}


def test_nested_data_shape():
    raw = {"success": True, "data": {"markdown": "# Acme Corp", "metadata": {"sourceURL": "https://acme.example.com"}}}
    out = extract_markdown_and_source_url(raw)
    assert out == {"markdown": "# Acme Corp", "source_url": "https://acme.example.com"}


def test_metadata_url_fallback_key():
    raw = {"markdown": "# Acme Corp", "metadata": {"url": "https://acme.example.com"}}
    out = extract_markdown_and_source_url(raw)
    assert out["source_url"] == "https://acme.example.com"


def test_missing_metadata_returns_none_source_url():
    raw = {"markdown": "# Acme Corp"}
    out = extract_markdown_and_source_url(raw)
    assert out == {"markdown": "# Acme Corp", "source_url": None}


def test_reads_from_file(tmp_path):
    raw = {"markdown": "# Acme Corp", "metadata": {"sourceURL": "https://acme.example.com"}}
    path = tmp_path / "firecrawl_response.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    out = extract_markdown_and_source_url(path)
    assert out == {"markdown": "# Acme Corp", "source_url": "https://acme.example.com"}
