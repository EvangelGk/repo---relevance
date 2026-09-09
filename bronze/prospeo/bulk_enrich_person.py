"""Prospeo's Bulk Enrich Person endpoint - resolves up to 50 leads per
call from name + company alone (no LinkedIn URL required as input),
returning each match's full Person Object, which includes `linkedin_url`
(confirmed present in that schema per prospeo.io/api-docs/person-object,
2026-09-09).

This is the "why not just bulk-enrich the people we already found"
alternative to a Prospeo-search + Claygent waterfall: Clay's own people
search (bronze/clay/search.py) never returns a LinkedIn URL at all
(confirmed empirically against a real Synthesa run - no `linkedin_url`
field anywhere in Clay's raw person payload, and no such field in Clay's
people field catalog either). This module backfills it onto an existing
name+company list - including one sourced from Clay, not just from
Prospeo's own search_person().

Request/response shape confirmed against prospeo.io/api-docs/
bulk-enrich-person, 2026-09-09 - the docs' own worked example:
    {"only_verified_email": true, "enrich_mobile": true,
     "data": [{"identifier": "1", "full_name": "...", "company_website": "..."}]}
    -> {"error": false, "total_cost": N, "matched": [...],
        "not_matched": ["2", "3"], "invalid_datapoints": ["4"]}
"""
import re
from typing import Any, Dict, List

from . import _http

_MAX_BATCH_SIZE = 50

# Confirmed live 2026-09-09, against a real not_matched->matched flip on
# the Synthesa people table: Clay's `name` field for senior medical/pharma
# people routinely carries trailing credentials ("Helen (Heleen) Sairany,
# PharmD, MBA, BCACP"), and this noise measurably suppresses Prospeo
# matches - "Filip Knop" and "Asif Khan" both matched only after their
# raw Clay names ("Filip K. Knop", "Asif Khan MPharm GPC MBA") were
# cleaned. Clay's own first_name/last_name split can't be trusted as a
# ready-made fix either - it's broken by the same noise (`last_name` comes
# back as "FAPCR" or "BCACP", credential abbreviations, not real
# surnames), so cleaning has to happen here, not by trusting Clay's split.
_CREDENTIALS = frozenset(
    name.upper()
    for name in (
        "MD", "PhD", "PharmD", "MBA", "MSc", "MS", "MA", "BA", "BS", "BSc",
        "RN", "RPh", "DDS", "DO", "JD", "CPA", "MPH", "MPharm", "DVM", "EdD",
        "BCACP", "BCIDP", "GPC", "FAPCR", "EMSHA", "LSSBBP", "MCh", "FACP",
        "FACC", "FRCP", "MRCP", "FAAP", "MSPH", "MHA", "MPA",
    )
)
_TITLES = frozenset(("DR", "PROF", "MR", "MRS", "MS", "MX"))

_PAREN_RE = re.compile(r"\s*\([^)]*\)")


def clean_person_name(raw_name: str) -> str:
    """Strips parenthetical nicknames, leading titles (Dr/Prof/...), single-
    letter middle initials, and trailing professional credentials
    (MD/PhD/MBA/...) off a Clay-style display name, leaving the plain
    first+last (+middle, if a real name) name Prospeo's matcher expects.

    Deliberately a curated denylist, not a generic "short/all-caps token"
    heuristic - a real surname that happens to be short (e.g. "Oz", "Ng")
    must never be stripped. An unlisted credential simply won't be
    stripped, which just leaves today's status quo (send the noisy token
    through), not a new failure mode.

    Never strips down to fewer than 2 tokens - a lone first name is worse
    for matching than a name with one unstripped trailing credential."""
    name = _PAREN_RE.sub("", raw_name)
    # Commas are just another credential separator here ("MD, MBA, FAPCR"),
    # not meaningful punctuation to preserve once we're tokenizing.
    tokens = name.replace(",", " ").split()
    if not tokens:
        return raw_name.strip()

    if tokens[0].replace(".", "").upper() in _TITLES and len(tokens) > 2:
        tokens = tokens[1:]

    while len(tokens) > 2 and tokens[-1].replace(".", "").upper() in _CREDENTIALS:
        tokens = tokens[:-1]

    # Single-letter middle initials ("Filip K. Knop" -> "Filip Knop") -
    # only interior tokens, and only down to a 2-token floor, so a
    # genuine one-word middle name is never touched.
    if len(tokens) > 2:
        tokens = [
            t
            for i, t in enumerate(tokens)
            if not (0 < i < len(tokens) - 1 and len(t.replace(".", "")) == 1)
        ]

    return " ".join(tokens) if len(tokens) >= 2 else name.strip()


def bulk_enrich_person(
    leads: List[Dict[str, Any]],
    only_verified_email: bool = True,
    enrich_mobile: bool = False,
    only_verified_mobile: bool = False,
) -> Dict[str, Any]:
    """`leads`: up to 50 dicts, each with an `identifier` (any string you
    generate, used to correlate results back to your own rows) plus one of
    the input combinations Prospeo documents: `first_name`+`last_name` (or
    `full_name`) + `company_name`/`company_website`/`company_linkedin_url`,
    a bare `linkedin_url`, a bare `email`, or a `person_id` from a prior
    search_person() result.

    Raises ValueError above the 50-lead cap rather than silently
    truncating - a caller batching a larger list should chunk it itself
    and see every batch's own matched/not_matched split.

    Returns Prospeo's raw response unmodified: {"matched": [...],
    "not_matched": [...], "invalid_datapoints": [...], "total_cost": int,
    "error": bool}."""
    if len(leads) > _MAX_BATCH_SIZE:
        raise ValueError(
            f"bulk_enrich_person accepts at most {_MAX_BATCH_SIZE} leads per call, got {len(leads)}"
        )

    body: Dict[str, Any] = {
        "only_verified_email": only_verified_email,
        "enrich_mobile": enrich_mobile,
        "only_verified_mobile": only_verified_mobile,
        "data": leads,
    }
    return _http.post("/bulk-enrich-person", body)
