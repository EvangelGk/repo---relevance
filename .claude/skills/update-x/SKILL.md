---
name: update-x
description: Generalizes update-orchestrator's re-check-and-propose pattern to ANY file, folder, module, source, connector, or concept in this repo (invoke as "/update-x <target>", e.g. /update-x foreman, /update-x contracts.py, /update-x the people connector, /update-x prospeo). Re-derives the target's dependency surface from the repo as it exists right now, finds what's out of sync, and proposes fixes - never edits anything itself, always waits for explicit per-item approval. Use whenever a target other than silver_orchestrator/ itself has changed and something else in the repo (a doc, a connector, a contract, a skill, a README) might now be stale relative to it.
---

# update-x

## Why this exists

`update-orchestrator` is one fixed, pinned instance of a pattern this
repo needs everywhere, not just for `silver_orchestrator/`: something
changes, and everything that depends on it, documents it, or assumes its
old shape needs a look. `context-sync` already delegates to
`update-orchestrator` specifically for orchestrator-shaped changes, but
has no equivalent delegate for a change to, say, `silver/foreman/`,
`silver/prospeo/`, a connector, or a single file. `update-x` is that
general delegate - `<x>` is whatever the user names, resolved fresh
against the repo's current tree every run, never a fixed target list.

**This never hardcodes what "x" can be, or what a target's dependents
are** - every list below is rebuilt by searching the live repo each time
this runs, specifically because this repo's own source list,
company/people splits, and universal/secondary tiers have already changed
more than once since being introduced (see `CLAUDE.md`'s dated addenda)
and will keep changing.

## 0. Resolve `<x>` to real, current locations - don't assume a path

The user names `<x>` loosely (a folder name, a filename, a package, a
concept like "the people connector" or "founded_year"). Resolve it live:

- If it looks like a path, confirm it exists (`find`/`ls`).
- Otherwise, search for it: `grep -ril "<x>"` across `silver/`, `bronze/`,
  `client_context/`, `.claude/skills/`, and the root-level docs
  (`CLAUDE.md`, `ARTEMIS_CONTEXT.md`, any other `*.md` at repo root), plus
  a filename/foldername match (`find . -iname "*<x>*"`).
- If nothing resolves, say so plainly and ask for the specific path or
  module - do not guess.

State back what you resolved `<x>` to (one or more concrete paths) before
continuing, so the human can correct a wrong guess before the rest of the
run is spent on it.

## 1. Build `<x>`'s actual dependency surface, fresh, every run

None of these are a fixed list - rebuild each by searching the repo as it
stands right now:

1. **Direct dependents**: everything that imports `<x>`'s module/function
   path, or reads a field/key it produces (`grep` the import path and,
   for a datapoint/field, its dict key, across `silver/` and `bronze/`).
2. **Contract dicts**: every `*_CONTRACTS: Dict[str, DatapointContract]`
   currently defined in `silver/silver_orchestrator/contracts.py` (grep
   for the pattern, don't name the dicts) - does any of them reference a
   field `<x>` produces, and is that entry still accurate?
3. **Connectors**: every file actually named `connector.py` under
   `silver/` (`find silver -name connector.py`, don't assume a fixed
   count or fixed names) - does any read `<x>`'s output, and does its
   docstring still describe `<x>`'s current shape?
4. **Orchestrator-level files**: whatever currently lives under
   `silver/silver_orchestrator/` (`ls` it fresh - `schema_gate.py`,
   `quality_score.py`, `drift.py`, `triage.py` exist today, but don't
   name them from memory, list them) - does any hard-require, penalize,
   or drift-track something about `<x>` that's now wrong?
5. **READMEs**: `<x>`'s own folder's `README.md` if it has one, plus any
   other `README.md` that mentions `<x>` (grep).
6. **Skills**: every `.claude/skills/*/SKILL.md` whose body mentions
   `<x>`'s file/folder/import path or field name (grep the skills
   directory - don't assume which skills are affected).
7. **Root docs**: `CLAUDE.md`'s Layout block and addenda, and any other
   project doc, whose description of `<x>` or of the repo's shape around
   it might now be stale.

## 2. Diff current reality against every one of those, and list gaps

For each dependent found in step 1, compare what it currently says/does
against what `<x>` actually does today. A gap is: a stale doc/README
describing an old shape (a redefinition, like `universal/`'s 2026-09-09
one, that some other file never picked up); a missing contract or
connector entry for a field `<x>` now emits; a skill whose worked
examples now name something removed or renamed; anything else
`update-orchestrator`'s own checklist would flag if `<x>` happened to be
inside `silver_orchestrator/`.

## 3. Output format - identical to update-orchestrator's, mandatory

For every gap, one numbered block in exactly this shape (verbatim - this
is not optional formatting):

> **N. WHAT:** <the specific gap, named by file + field/section>
> **WHY:** <what breaks or silently degrades if left>
> **PROPOSAL:** <the concrete change>
> **PROS / CONS:** <bulleted, honest, including the cost of doing it>
> **ALTERNATIVE (2nd proposal):** <a genuinely different approach>
> **PROS / CONS (alternative):** <same rigor>

Then stop and ask: "Which numbers should I apply?" Do not write any code
change until the human answers with specific numbers (or "all").

If step 1/2 finds nothing out of sync, say that plainly - don't
manufacture a gap just to have something to report.

## Hard rules

- Never runs `git commit`/`push`/`clean`/`reset --hard`.
- Never edits a file the human didn't explicitly approve by number in
  this same session.
- Read-only until that approval.

## Relationship to `update-orchestrator` and `context-sync`

`update-orchestrator` stays as the pinned, always-on instance of this
pattern scoped specifically to `silver_orchestrator/` (per its own
vital-priority framing) - it is functionally what you'd get from
`/update-x silver_orchestrator`, kept as its own named skill since that
package is the one every source funnels through and is worth invoking by
a short, unambiguous name on its own. `context-sync` is the automatic,
git-hook-triggered version that decides *when* a check is needed, and
today only delegates to `update-orchestrator` for orchestrator-shaped
changes; it does not invoke `update-x` automatically. Wiring
`context-sync` to delegate to `update-x` for non-orchestrator slices too
is a real option worth considering, but it's a change to `context-sync`
itself - not made here, and not assumed.
