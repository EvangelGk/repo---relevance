---
name: context-sync
description: Rereads the whole repo, diffs it against the last recorded snapshot, and produces one consolidated proposal report covering every skill, doc, and dependent code file the changes touched — plus a delegated check of silver_orchestrator/ via update-orchestrator. Read-only: never edits anything itself. Meant to be run automatically (via the post-commit git hook set up alongside this skill) so the repo owner never has to remember to trigger it by hand.
---

# context-sync

## What this run does, in order
1. Load `.claude/context-sync/last-sync.json`. Compute the current
   `{file_path: sha256}` map for every tracked file. Diff the two —
   this is your changed-files list, independent of git's own diff (so
   it also catches changes made outside a commit).
2. For every changed file, classify its blast radius:
   - Touches `silver/silver_orchestrator/*` or adds a new source/
     connector/contract → delegate that whole slice to the
     `update-orchestrator` skill's checklist and fold its output in
     under its own heading, unmodified.
   - Touches any `silver/*` or `bronze/*` module referenced by a
     `.claude/skills/*/SKILL.md` file (grep each skill file's body for
     the changed module's import path or filename) → that skill needs a
     look.
   - Touches repo scope/shape in a way `CLAUDE.md`'s Layout block or
     `ARTEMIS_CONTEXT.md`'s scope section describes → those two docs
     need a look.
   - Adds a new field to a connector's output (`silver/company/
     connector.py`, `silver/people/connector.py`) not yet listed in the
     repo owner's universal/secondary spec → flag as a spec-drift item,
     not just a doc item.
   - Anything else with a `README.md` in its own folder → that README
     needs a look.
3. Produce ONE report, grouped under these headings, each item using the
   mandatory template below:
   - `## Skills to update`
   - `## Docs to update` (CLAUDE.md, ARTEMIS_CONTEXT.md, per-folder READMEs)
   - `## Orchestrator changes` (the delegated update-orchestrator output)
   - `## Other dependent code`
4. Write the report to
   `.claude/context-sync/pending-report-<UTC timestamp>.md`. Do not
   edit any other file in this run.
5. Only after every item in a report has been explicitly resolved
   (approved-and-applied, or explicitly rejected) by the human in a
   follow-up interactive session, update `last-sync.json` to the new
   snapshot. An unresolved report means the next run's diff still
   includes those files — nothing is silently marked done.

## Output format per item — identical to update-orchestrator's, mandatory
> **N. WHAT / WHY / PROPOSAL / PROS-CONS / ALTERNATIVE + PROS-CONS**

## Hard rules
- Never edits a skill file, a doc, or any code file directly. Ever.
- Never runs `git commit`/`push`/`clean`/`reset --hard`.
- If invoked non-interactively (from the git hook, see below), it MUST
  stop after writing the report file — it cannot ask a question or wait
  for input in that context, so it must not attempt to.
