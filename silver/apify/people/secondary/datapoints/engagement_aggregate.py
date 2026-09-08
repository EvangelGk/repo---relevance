"""function_engagement_aggregate(posts: list[dict]) -> dict

Aggregates a list of LinkedIn post engagement dicts
(`{"reactions": int, "comments": int}`, extra keys ignored) into:

    {"total_posts", "total_reactions", "total_comments", "avg_reactions_per_post"}

Missing `reactions`/`comments` on a given post count as 0, not a skip -
partial engagement data is still real engagement data.
"""
from typing import Any, Dict, List, Optional


def function_engagement_aggregate(posts: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    posts = posts or []
    total_posts = len(posts)
    total_reactions = sum(int(p.get("reactions") or 0) for p in posts)
    total_comments = sum(int(p.get("comments") or 0) for p in posts)
    avg_reactions = round(total_reactions / total_posts, 2) if total_posts else None

    return {
        "total_posts": total_posts,
        "total_reactions": total_reactions,
        "total_comments": total_comments,
        "avg_reactions_per_post": avg_reactions,
    }
