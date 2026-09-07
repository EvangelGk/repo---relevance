---
name: explain-artemis-context
description: Explain how this repo (the Silver layer - firecrawl/ + silver_orchestrator/) fits into the broader Artemis/Hermes list-building pipeline, its current build state, and what's explicitly out of scope here. Use when onboarding to this repo, before proposing a change that touches orchestrator-level (quota/DNC/Supabase/HITL) concerns, or when asked "how does this relate to Artemis."
---

# Explaining this repo's place in Artemis

This repo is not part of the `gtm-core` monorepo and has no live sync to
it. `ARTEMIS_CONTEXT.md` at the repo root is a point-in-time distillation
of that monorepo's Artemis/Hermes docs, written so a session working here
doesn't need that monorepo attached to stay oriented. Treat it as a brief,
not a source of truth for the other repo - if something here conflicts
with what someone says the actual Artemis docs now say, the actual docs
win, and `ARTEMIS_CONTEXT.md` is stale and due for a resync.

## What to do when this skill is invoked

1. Read `ARTEMIS_CONTEXT.md` in full - it's short by design.
2. Answer the specific question asked (where does this repo fit / what's
   the 9-step Artemis checklist / what's explicitly out of scope here)
   directly from that file. Don't speculate beyond what it states.
3. If the question is about something `ARTEMIS_CONTEXT.md` doesn't cover
   (a governance rule, a skill spec, a client-specific detail), say so
   plainly rather than guessing - that detail lives in the other monorepo,
   not here.
4. If you're about to build something that sounds like it belongs to the
   orchestrator layer proper (quota tracking, DNC suppression, a shared
   ledger, HITL taxonomy-mint routing) - check `ARTEMIS_CONTEXT.md`'s
   "explicitly out of scope" section first. This repo's own
   `SilverOrchestrator` is a Silver-layer-only gate, not the Artemis
   orchestrator - don't let the two blur together.

## Keeping this in sync

There is no automation for this yet. When the Cowork-side Project docs
(artemis-hermes-orchestration-strategy.md, the orchestrator
proposal/evaluation docs, the Larridin GTM Thesis) change in a way that
affects this repo's assumptions, `ARTEMIS_CONTEXT.md` needs a manual
resync from that session - flag it to the person running this repo rather
than silently trusting a possibly-stale file.
