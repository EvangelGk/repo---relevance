"""
silver/foreman/source_priority_resolve.py

"The foreman" -- v2, redesigned for N sources, not 2.

The previous pass (shared_functions.py + founded_year.py, both deleted,
neither resurrected here under any name) hardcoded the foreman to exactly
two positional (value, source) pairs and pushed a 3rd candidate into a
chained-call hack. That was wrong: two sources aren't the mechanism, MANY
sources competing is the mechanism -- 2, 3, or 15 should all be the same
call. Arity is data (the length of `candidates`), never code.

Two design pieces:

1. `candidates: list[Candidate]` -- one dict per competing source,
   `{"source": str, "value": Any, "meta": dict | omitted}`. Any length,
   including 1 (nothing to resolve, passthrough) and 0.

2. `priority_rule["criteria"]: list[CriterionSpec]` -- an ORDERED list of
   tie-breakers, not a single static rank. `static_rank` is one criterion
   type among several (pluggable via CRITERIA_REGISTRY below); a field
   can chain more than one when rank alone doesn't decide. This is what
   "rules and criteria to decide priority, customized by datapoint" means
   concretely: each datapoint in priority_rules.py picks which criteria
   apply to IT, in what order, not a single global source ladder.

Adding a new criterion type (e.g. "prefer_verified_domain") means adding
one function to CRITERIA_REGISTRY -- the resolve loop below never changes.
Adding a 4th, 10th, or 15th competing source for an existing datapoint
means adding one more dict to that call's `candidates` list -- the
function signature never changes either.
"""

from typing import Any, Callable, Optional, TypedDict


class Candidate(TypedDict, total=False):
    source: str
    value: Any
    meta: dict  # optional, per-candidate: e.g. {"observed_at": "...", "confidence": 0.9, "is_structured": True}


class CriterionSpec(TypedDict, total=False):
    type: str          # key into CRITERIA_REGISTRY, e.g. "static_rank", "prefer_structured", "most_recent",
                        # "highest_confidence", "majority_vote"
    rank: list[str]     # used by "static_rank": source names, highest priority first
    meta_key: str       # used by criteria that read Candidate["meta"], e.g. "observed_at" / "confidence" / "is_structured"


class PriorityRule(TypedDict, total=False):
    criteria: list[CriterionSpec]     # ordered tie-breakers; first one that narrows to a single group wins
    normalize: Optional[str]          # "int" | "lower_strip" | None -- applied before comparing values for agreement


class ResolvedValue(TypedDict):
    value: Any
    source: Optional[str]
    conflict: bool          # True iff 2+ live candidates existed and disagreed after normalization
    ambiguous: bool          # True iff every criterion was applied and a tie still remained (deterministic fallback used)
    raw_values: dict[str, Any]   # {source: value} for every candidate passed in, including empties -- never dropped
    candidate_count: int


def _is_empty(v: Any) -> bool:
    return v is None or v == "" or v == []


def _normalize(value: Any, normalize: Optional[str]) -> Any:
    if normalize == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if normalize == "lower_strip":
        return str(value).strip().lower()
    return value


# --- criteria registry -----------------------------------------------------
# Each criterion takes the current list of tied VALUE-GROUPS (a group = all
# live candidates sharing one normalized value) and narrows it. If a
# criterion can't distinguish, it returns the groups unchanged and the next
# criterion in the list gets a turn.

def _crit_static_rank(groups: list, spec: CriterionSpec) -> list:
    rank = spec.get("rank", [])
    def best_rank(group):
        ranks = [rank.index(c["source"]) for c in group if c["source"] in rank]
        return min(ranks) if ranks else len(rank)  # sources absent from `rank` sort last, never crash
    m = min(best_rank(g) for g in groups)
    return [g for g in groups if best_rank(g) == m]


def _crit_prefer_structured(groups: list, spec: CriterionSpec) -> list:
    key = spec.get("meta_key", "is_structured")
    def has_structured(group):
        return any(c.get("meta", {}).get(key) for c in group)
    structured = [g for g in groups if has_structured(g)]
    return structured or groups  # if nobody claims structured, this criterion abstains


def _crit_most_recent(groups: list, spec: CriterionSpec) -> list:
    key = spec.get("meta_key", "observed_at")
    def latest(group):
        times = [c.get("meta", {}).get(key) for c in group if c.get("meta", {}).get(key)]
        return max(times) if times else None
    dated = [(g, latest(g)) for g in groups]
    if not any(t is not None for _, t in dated):
        return groups  # nobody has a timestamp -- abstain
    best = max((t for _, t in dated if t is not None), default=None)
    return [g for g, t in dated if t == best] or groups


def _crit_highest_confidence(groups: list, spec: CriterionSpec) -> list:
    key = spec.get("meta_key", "confidence")
    def best_conf(group):
        confs = [c.get("meta", {}).get(key) for c in group if c.get("meta", {}).get(key) is not None]
        return max(confs) if confs else None
    scored = [(g, best_conf(g)) for g in groups]
    if not any(c is not None for _, c in scored):
        return groups
    best = max((c for _, c in scored if c is not None), default=None)
    return [g for g, c in scored if c == best] or groups


def _crit_majority_vote(groups: list, spec: CriterionSpec) -> list:
    m = max(len(g) for g in groups)
    return [g for g in groups if len(g) == m]


CRITERIA_REGISTRY: dict[str, Callable[[list, CriterionSpec], list]] = {
    "static_rank": _crit_static_rank,
    "prefer_structured": _crit_prefer_structured,
    "most_recent": _crit_most_recent,
    "highest_confidence": _crit_highest_confidence,
    "majority_vote": _crit_majority_vote,
}


def function_source_priority_resolve(
    candidates: list,
    priority_rule: "PriorityRule",
) -> "ResolvedValue":
    """
    The foreman. N competing (source, value) candidates in, one
    authoritative value out. N is whatever `len(candidates)` is -- 1, 2,
    3, 15 -- the function never branches on how many showed up.

    Resolution, every call, in this order:
      1. Drop empty/null candidates. 0 left -> value=None, no conflict.
         1 left -> that one, no conflict (not a real contest).
      2. 2+ live candidates: group by normalized value. All one group
         (everyone agrees) -> that value, no conflict.
      3. 2+ distinct groups (genuine disagreement) -> walk
         priority_rule["criteria"] in order, each one narrowing the group
         set, until exactly one group remains or the list is exhausted.
      4. Still 2+ groups after every criterion -> deterministic fallback
         (first group, by original candidate order) + ambiguous=True, so
         a human can find every field that criteria alone couldn't settle.

    raw_values always contains every candidate passed in, resolved or not
    -- nothing is ever silently dropped, win or lose.
    """
    raw_values = {c["source"]: c.get("value") for c in candidates}

    live = [c for c in candidates if not _is_empty(c.get("value"))]
    if not live:
        return {"value": None, "source": None, "conflict": False, "ambiguous": False,
                "raw_values": raw_values, "candidate_count": len(candidates)}
    if len(live) == 1:
        only = live[0]
        return {"value": only["value"], "source": only["source"], "conflict": False, "ambiguous": False,
                "raw_values": raw_values, "candidate_count": len(candidates)}

    normalize = priority_rule.get("normalize")
    groups_by_key: dict = {}
    order: list = []
    for c in live:
        key = _normalize(c["value"], normalize)
        if key not in groups_by_key:
            groups_by_key[key] = []
            order.append(key)
        groups_by_key[key].append(c)
    groups = [groups_by_key[k] for k in order]

    if len(groups) == 1:
        winner = groups[0][0]
        return {"value": winner["value"], "source": winner["source"], "conflict": False, "ambiguous": False,
                "raw_values": raw_values, "candidate_count": len(candidates)}

    for spec in priority_rule.get("criteria", []):
        fn = CRITERIA_REGISTRY.get(spec["type"])
        if fn is None:
            raise ValueError(f"Unknown priority criterion type: {spec['type']!r}")
        groups = fn(groups, spec)
        if len(groups) == 1:
            break

    ambiguous = len(groups) > 1
    winner = groups[0][0]
    return {"value": winner["value"], "source": winner["source"], "conflict": True, "ambiguous": ambiguous,
            "raw_values": raw_values, "candidate_count": len(candidates)}
