"""
silver/foreman/test_foreman.py

pytest-native (matches this repo's convention, e.g.
silver/apify/company/secondary/tests/test_headcount_band.py) - no
sys.path hacking, relies on pyproject.toml's `pythonpath = ["."]`.
Run with `poetry run pytest silver/foreman -q`.

Covers: 0/1/2/3-candidate basics, explicit 5- and 15-source scenarios
(scalability is the whole point of this redesign - proven, not just
claimed), criteria chaining (a static_rank tie falling through to
majority_vote), prefer_structured, most_recent with metadata timestamps,
the exhausted-criteria ambiguous fallback, and an explicit error on an
unregistered criterion type.
"""
import pytest

from silver.foreman.source_priority_resolve import function_source_priority_resolve
from silver.foreman.priority_rules import PRIORITY_RULES

FOUNDED_YEAR_RULE = PRIORITY_RULES["founded_year"]  # rank: crunchbase > firecrawl > apify


def C(source, value, meta=None):
    c = {"source": source, "value": value}
    if meta:
        c["meta"] = meta
    return c


def test_zero_candidates_returns_none_no_conflict():
    result = function_source_priority_resolve([], FOUNDED_YEAR_RULE)
    assert result == {
        "value": None, "source": None, "conflict": False, "ambiguous": False,
        "raw_values": {}, "candidate_count": 0,
    }


def test_one_candidate_is_passthrough_not_a_contest():
    result = function_source_priority_resolve([C("apify", 2020)], FOUNDED_YEAR_RULE)
    assert result["value"] == 2020
    assert result["source"] == "apify"
    assert result["conflict"] is False


def test_two_candidates_agree_after_int_normalize():
    result = function_source_priority_resolve(
        [C("apify", "2015"), C("crunchbase", 2015)], FOUNDED_YEAR_RULE
    )
    assert result["value"] == "2015"
    assert result["conflict"] is False


def test_two_candidates_disagree_rank_decides():
    result = function_source_priority_resolve(
        [C("apify", 2020), C("crunchbase", 2015)], FOUNDED_YEAR_RULE
    )
    assert result["value"] == 2015
    assert result["source"] == "crunchbase"
    assert result["conflict"] is True


def test_three_candidates_native_no_chaining_hack_needed():
    result = function_source_priority_resolve(
        [C("apify", 2021), C("firecrawl", 2018), C("crunchbase", 2015)], FOUNDED_YEAR_RULE
    )
    assert result["value"] == 2015
    assert result["source"] == "crunchbase"
    assert result["conflict"] is True


def test_three_candidates_top_rank_absent_next_rank_wins():
    result = function_source_priority_resolve(
        [C("apify", 2021), C("firecrawl", 2018), C("crunchbase", None)], FOUNDED_YEAR_RULE
    )
    assert result["value"] == 2018
    assert result["source"] == "firecrawl"
    assert result["conflict"] is True


def test_three_candidates_all_agree_no_conflict():
    result = function_source_priority_resolve(
        [C("apify", 2015), C("firecrawl", 2015), C("crunchbase", 2015)], FOUNDED_YEAR_RULE
    )
    assert result["value"] == 2015
    assert result["conflict"] is False


def test_three_candidates_all_empty():
    result = function_source_priority_resolve(
        [C("apify", None), C("firecrawl", ""), C("crunchbase", None)], FOUNDED_YEAR_RULE
    )
    assert result == {
        "value": None, "source": None, "conflict": False, "ambiguous": False,
        "raw_values": {"apify": None, "firecrawl": "", "crunchbase": None},
        "candidate_count": 3,
    }


def test_five_sources_scalability_all_pairwise_disagree():
    rank5 = {"criteria": [{"type": "static_rank", "rank": ["s1", "s2", "s3", "s4", "s5"]}], "normalize": "int"}
    result = function_source_priority_resolve(
        [C("s5", 5), C("s3", 3), C("s1", 1), C("s4", 4), C("s2", 2)], rank5
    )
    assert result["value"] == 1
    assert result["source"] == "s1"
    assert result["conflict"] is True


def test_fifteen_sources_only_one_has_data():
    rank15 = {"criteria": [{"type": "static_rank", "rank": [f"src{i}" for i in range(15)]}], "normalize": "int"}
    candidates = [C(f"src{i}", None) for i in range(15)]
    candidates[11] = C("src11", 999)
    result = function_source_priority_resolve(candidates, rank15)
    assert result["value"] == 999
    assert result["source"] == "src11"
    assert result["conflict"] is False
    assert len(result["raw_values"]) == 15  # every candidate kept, none dropped


def test_fifteen_sources_three_disagree_rank_among_those_decides():
    rank15 = {"criteria": [{"type": "static_rank", "rank": [f"src{i}" for i in range(15)]}], "normalize": "int"}
    candidates = [C(f"src{i}", None) for i in range(15)]
    candidates[2] = C("src2", 100)
    candidates[9] = C("src9", 200)
    candidates[14] = C("src14", 300)
    result = function_source_priority_resolve(candidates, rank15)
    assert result["value"] == 100
    assert result["source"] == "src2"  # outranks src9 and src14
    assert result["conflict"] is True


def test_chained_criteria_static_rank_tie_falls_through_to_majority_vote():
    chained = {
        "criteria": [
            {"type": "static_rank", "rank": ["known_a"]},  # unknown_x/unknown_y both sort last -> tie
            {"type": "majority_vote"},
        ],
        "normalize": None,
    }
    result = function_source_priority_resolve(
        [C("unknown_x", "east"), C("unknown_y", "east"), C("unknown_z", "west")], chained
    )
    assert result["value"] == "east"  # 2 votes beats 1
    assert result["conflict"] is True


def test_prefer_structured_criterion():
    structured_rule = {
        "criteria": [
            {"type": "prefer_structured"},
            {"type": "static_rank", "rank": ["apify", "firecrawl"]},
        ],
        "normalize": "lower_strip",
    }
    result = function_source_priority_resolve(
        [
            C("apify", "New York", meta={"is_structured": False}),
            C("firecrawl", "NYC", meta={"is_structured": True}),
        ],
        structured_rule,
    )
    assert result["value"] == "NYC"
    assert result["source"] == "firecrawl"
    assert result["conflict"] is True


def test_most_recent_criterion_uses_metadata_timestamp():
    recency_rule = {"criteria": [{"type": "most_recent", "meta_key": "observed_at"}], "normalize": None}
    result = function_source_priority_resolve(
        [
            C("apify", "500", meta={"observed_at": "2026-01-01"}),
            C("firecrawl", "620", meta={"observed_at": "2026-08-01"}),
        ],
        recency_rule,
    )
    assert result["value"] == "620"
    assert result["source"] == "firecrawl"
    assert result["conflict"] is True


def test_ambiguous_fallback_when_criteria_exhausted_still_tied():
    no_tiebreak_rule = {"criteria": [{"type": "static_rank", "rank": []}], "normalize": None}
    result = function_source_priority_resolve([C("x", "a"), C("y", "b")], no_tiebreak_rule)
    assert result["conflict"] is True
    assert result["ambiguous"] is True
    assert result["value"] == "a"  # first candidate in original order, deterministic
    assert result["source"] == "x"


def test_unknown_criterion_type_raises_instead_of_guessing():
    with pytest.raises(ValueError):
        function_source_priority_resolve(
            [C("x", 1), C("y", 2)], {"criteria": [{"type": "not_a_real_criterion"}]}
        )
