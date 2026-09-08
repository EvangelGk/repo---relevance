from silver.apify.people.secondary.datapoints.bio_entity_extract import function_bio_entity_extract

_SAMPLE_BIO = (
    "Building at Acme Corp. Formerly @ Globex Inc. "
    "Find my work at https://example.com/portfolio and follow @janedoe on socials."
)


def test_extracts_urls_companies_and_handles():
    result = function_bio_entity_extract(_SAMPLE_BIO)
    assert result["mentioned_urls"] == ["https://example.com/portfolio"]
    assert "Acme Corp" in result["mentioned_companies"]
    assert "Globex Inc" in result["mentioned_companies"]
    assert result["mentioned_handles"] == ["janedoe"]


def test_empty_bio():
    result = function_bio_entity_extract(None)
    assert result == {"mentioned_urls": [], "mentioned_companies": [], "mentioned_handles": []}
