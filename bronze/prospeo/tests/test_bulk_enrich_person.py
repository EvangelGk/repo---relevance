"""Tests for bronze.prospeo.bulk_enrich_person - HTTP is mocked throughout
(patching bronze.prospeo.bulk_enrich_person._http.post), no real network
call."""
from unittest.mock import patch

import pytest

from bronze.prospeo.bulk_enrich_person import bulk_enrich_person, clean_person_name


def test_sends_leads_under_the_data_key():
    leads = [{"identifier": "1", "full_name": "Eva Kiegler", "company_website": "intercom.com"}]
    with patch("bronze.prospeo.bulk_enrich_person._http.post", return_value={}) as mock_post:
        bulk_enrich_person(leads)

    mock_post.assert_called_once_with(
        "/bulk-enrich-person",
        {
            "only_verified_email": True,
            "enrich_mobile": False,
            "only_verified_mobile": False,
            "data": leads,
        },
    )


def test_enrich_mobile_flag_passes_through():
    with patch("bronze.prospeo.bulk_enrich_person._http.post", return_value={}) as mock_post:
        bulk_enrich_person(
            [{"identifier": "1", "full_name": "X", "company_name": "Y"}], enrich_mobile=True
        )

    _, body = mock_post.call_args[0]
    assert body["enrich_mobile"] is True


def test_more_than_fifty_leads_raises():
    leads = [{"identifier": str(i)} for i in range(51)]
    with pytest.raises(ValueError):
        bulk_enrich_person(leads)


def test_returns_raw_response_unmodified():
    fake_response = {
        "error": False,
        "total_cost": 1,
        "matched": [{"identifier": "1", "person": {"linkedin_url": "https://linkedin.com/in/x"}}],
        "not_matched": [],
        "invalid_datapoints": [],
    }
    with patch("bronze.prospeo.bulk_enrich_person._http.post", return_value=fake_response):
        result = bulk_enrich_person([{"identifier": "1", "full_name": "X", "company_name": "Y"}])

    assert result == fake_response


# Real names pulled from a live not_matched Prospeo response on the
# Synthesa people table (2026-09-09) - these are the actual cases that
# motivated clean_person_name(), not synthetic examples.
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Helen (Heleen) Sairany, PharmD, MBA, BCACP", "Helen Sairany"),
        ("Filip K. Knop", "Filip Knop"),
        ("Asif Khan MPharm GPC MBA", "Asif Khan"),
        ("Andrew Asante, PharmD", "Andrew Asante"),
        ("Elizabeth Charlotte Moser MD PhD MBA", "Elizabeth Charlotte Moser"),
        ("Dr Manish Verma MD", "Manish Verma"),
        ("Hani Al-Hashmi, MD, EMSHA, LSSBBP", "Hani Al-Hashmi"),
        ("Carlos Eid, MD", "Carlos Eid"),
        ("Kamran Mohiuddin MD, MBA, FAPCR", "Kamran Mohiuddin"),
        ("Hazem El Ashry, PhD., M.Sc., MBA", "Hazem El Ashry"),
    ],
)
def test_clean_person_name_strips_credentials_titles_and_initials(raw, expected):
    assert clean_person_name(raw) == expected


def test_clean_person_name_never_drops_to_a_single_token():
    # "Salvatore F." - Clay's own data is already truncated to a single
    # last-name initial; there's no real surname to recover, so this is
    # left as-is rather than stripped down to "Salvatore" alone.
    assert clean_person_name("Salvatore F.") == "Salvatore F."


def test_clean_person_name_leaves_a_plain_name_unchanged():
    assert clean_person_name("Ada Lovelace") == "Ada Lovelace"
