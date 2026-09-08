"""Prospeo intake loader - placeholder, no parsing logic yet.

Scaffolded 2026-09-08 as part of the source-first restructure
(silver/apify/, silver/firecrawl/, silver/prospeo/ each own their own
source's shape). Deliberately left unimplemented, pending an actual
Prospeo CSV export sample:

Expected input: a Prospeo CSV export, one row per person, already clean
(no markdown-scraping, no regex heuristics needed - unlike Firecrawl's
inputs).

Join key: LinkedIn URL or an internal `person_id` - UNDECIDED. Don't guess
which one Prospeo actually emits or which this pipeline should key on
until a real sample file is in hand; guessing wrong here would produce a
silently-broken join, which is worse than leaving this unbuilt.

Column handling (once built): pass through whatever columns the CSV
actually has rather than hardcoding an expected schema - Prospeo may
add/remove columns between exports. Every passed-through column gets a
companion `<field>_source: "prospeo"` tag, per this repo's
source-differentiator convention (see silver/people/connector.py).
"""
