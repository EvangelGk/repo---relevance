from silver.apify.people.secondary.datapoints.engagement_aggregate import function_engagement_aggregate


def test_empty():
    result = function_engagement_aggregate(None)
    assert result == {
        "total_posts": 0, "total_reactions": 0, "total_comments": 0, "avg_reactions_per_post": None,
    }


def test_aggregates_and_averages():
    posts = [
        {"reactions": 10, "comments": 2},
        {"reactions": 20, "comments": 5},
        {"reactions": 0},  # missing comments -> 0
    ]
    result = function_engagement_aggregate(posts)
    assert result["total_posts"] == 3
    assert result["total_reactions"] == 30
    assert result["total_comments"] == 7
    assert result["avg_reactions_per_post"] == 10.0
