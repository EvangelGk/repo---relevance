---
name: add-datapoint
description: Scaffold a new datapoint/extractor field for ANY source in this repo (Firecrawl, Apify, Prospeo, or a future source), for either company or people rows, at whichever tier that source/entity currently uses - by reading the target folder's own existing pattern and README instead of assuming Firecrawl's class-based pattern applies everywhere.
---

# Add a new datapoint function - any source, any entity, any tier

This repo does not have one datapoint pattern - it has one pattern per
source, and sources keep multiplying (Firecrawl today, Apify and Prospeo
added since, more likely later). Never assume "datapoint" means
"Firecrawl's `DataPointExtractor` + `REGISTRY`" - that is one source's
pattern, not the template. Every step below says "check the actual repo,
right now" rather than naming a fixed list, because the source list, the
company/people split, and the universal/secondary tiers have all changed
since this skill was first written and will keep changing.

## 0. Locate where this datapoint actually belongs - don't assume, look

**Which source?** Run `ls bronze/` and `ls silver/` (ignore `__pycache__`)
to see the sources that exist in this repo *today*. Confirm with the user
which one the new field belongs to if it isn't obvious from their request
- do not default to Firecrawl just because it was the first source built.

**Which entity - company, people, or neither?** Check whether
`silver/<source>/` splits into `company/`/`people/` subfolders. Some
sources do (Apify, Prospeo-for-people); some don't (Firecrawl is flat - it
only ever handles company pages today, so it has no `company/`/`people/`
split to begin with). If the source you picked has no such split yet and
the new field is genuinely about the *other* entity than what it
currently handles, that's a bigger structural decision (a new entity
split for that source) than "add one file" - stop and confirm that with
the user explicitly before scaffolding anything.

**Which tier - universal, secondary, or neither?** Check whether
`silver/<source>/<entity>/` splits into `universal/`/`secondary/`
subfolders. If it does, **read that folder's own `README.md` first** -
the definition of "universal" has been formally redefined before in this
repo (see `silver/apify/people/universal/README.md`'s own account of its
2026-09-09 redefinition), so the README on disk right now is the only
reliable definition, never a memorized one. State back to the user which
tier you're placing the new field in and why, quoting the current
README's own wording.

**A source/entity/tier combo with no existing folder at all** is a bigger
scaffold than a single file (see `silver/prospeo/people/universal/`,
which today is a loader stub with no `datapoints/` yet). If that's what
this request needs, say so and confirm the new folder's shape with the
user before creating anything - use the *nearest* sibling combo (same
source different entity, or same tier different source) as your proposed
template, not an invented new shape.

Before writing code, also confirm with the user (or infer from their
request):
- The function's snake_case name (filename, and - depending on the
  pattern in step 1 - the class `name` attribute or the function name).
- What it extracts, and from where (raw source record / prose / another
  already-computed field in the same row) - and, if there's a
  context-vs-fallback split, which one wins.
- What "empty" looks like for it (`None`? `[]`? `{}`?) and whether that's
  actually common on real records for this source - see `/review-contract`.

## 1. Copy the pattern that ALREADY LIVES in that exact folder

Open one existing file in the exact `silver/<source>/<entity>/<tier>/
datapoints/` folder (or the source's own datapoints folder, for a source
with no entity/tier split) you landed on in step 0, and copy its shape -
do not assume it looks like Firecrawl's. As of this writing, two shapes
coexist in this repo, but treat this as "what to check for," not a closed
list:

- **Class-based, self-registering** (Firecrawl's shape today): subclass a
  shared base extractor class, set a `name` attribute matching the
  filename, implement `extract(...)`, set the source-vocabulary attribute
  (`self._last_source` in Firecrawl) at every return point using whatever
  vocabulary words that base class's own docstring already documents for
  this source - don't invent a new one without a reason. Register it with
  one import line in that folder's own `__init__.py`; import order is
  execution order there, so position it after anything it reads and
  before anything that reads it.
- **Plain function, manually wired** (Apify's and Prospeo's shape today):
  one function per file, no base class, no registry. Wire it by hand into
  that exact folder's own `extract.py` (composing it alongside the
  others), and into `loader.py` too if the source needs one. If that
  folder has no `extract.py` yet, creating it is part of this task, not a
  prerequisite someone else already did.

If the folder you landed on in step 0 is empty and there is truly nothing
in it to copy from, say that explicitly and use the nearest sibling
combo's file as your reference instead - name which one and why, and
confirm before writing.

Return `None` / `[]` / `{}` for "nothing found" rather than a dict of all
sub-keys set to `None`, if the source's existing pattern already collapses
blank dicts downstream (Firecrawl's `Firecrawl._collapse_if_blank` does
this) - check whether the source you're in does this before hand-rolling
your own collapse.

## 2. Register or wire it, per the pattern chosen in step 1

Registry sources: the one `__init__.py` import line described above.
Plain-function sources: the `extract.py` (and `loader.py`) call described
above. Don't do both - only one applies, decided by what the folder
you're in actually does today.

## 3. Add a contract entry - find the right dict, don't assume its name

Run `grep -n "_CONTRACTS: Dict\[str, DatapointContract\] = {"
silver/silver_orchestrator/contracts.py` to get the CURRENT list of
contract dicts - do not hardcode which ones exist in this skill, that
list has grown before and will again. Find the one matching your
source+entity combo.

- **If a matching dict already exists**: add your entry there.
  `required=False` in the overwhelming majority of cases (flip to `True`
  only after checking with the user - reserved today for join-key-critical
  fields). `null_tolerance_pct` - estimate honestly from how often this
  signal appears on a typical real record for *this* source, with a
  trailing comment explaining the number, matching that dict's existing
  entries' style. `source_priority` - an ordered tuple matching exactly
  the source-vocabulary words this function can actually emit for this
  source (Firecrawl's vocabulary and Apify's are different - check the
  base class or the folder's own convention, don't reuse Firecrawl's
  words for an Apify field). `enum_values` - only for a controlled
  vocabulary; read the dataclass docstring in `contracts.py` before
  copying an existing nested-tuple exception.
- **If no dict exists yet for this source+entity**: that is exactly the
  trigger `/add-orchestrator-check` names for inventing a new contract
  dict. Stop here and run `/update-x contracts.py` (or
  `/add-orchestrator-check`) to get that reviewed and approved first,
  rather than hand-rolling a new `_CONTRACTS` dict inside this skill.

Full checklist for the contract entry itself once the dict is settled:
`/review-contract`.

## 4. Wire it into whatever actually consumes this source's row today

Don't assume `app.py`. Check, for the source you're in:

- **Does this source's row reach `app.py`'s Streamlit UI today?** (Today:
  Firecrawl's does, via `SilverOrchestrator.process_page()`; confirm the
  current state for any other source rather than assuming it does or
  doesn't.) If yes, and the new field reads a context/override key, add a
  matching widget to the "Optional context overrides" expander and the
  `overrides` dict on button click. If the new field has no override (a
  pure derivation), say explicitly in your summary that there's nothing
  to add here - don't silently skip the check.
- **Does this source's output feed a connector** (`silver/company/
  connector.py`, `silver/people/connector.py`, or whichever connector
  files currently exist - `find silver -name connector.py`, don't assume
  there are exactly two)? If the connector's own docstring shows it
  already reads this source for this entity, the new field likely needs a
  line there too (as a single-source tag, or via `silver/foreman/` if a
  second live candidate source for the same field already exists - see
  `silver/company/connector.py`'s `name` field for a worked example of
  the foreman path). If the connector doesn't read this source at all
  yet, wiring it in for the first time is a bigger decision than adding
  one field - flag it, don't fold it in silently.

A UI-override addition is worth the `/run-streamlit-ui` Playwright
drive-through per `CLAUDE.md`'s working agreements; a pure connector or
extraction-logic change is not.

## 5. Add tests, in that exact folder's own `tests/`

Add tests in the `tests/` directory that sits next to the folder you
scaffolded in step 1 (not a hardcoded path) - copy the test style already
used by a sibling test file in that same folder. At minimum: one
happy-path case against that folder's existing sample fixture (or a
purpose-built inline snippet if none fits), and one empty/negative case,
confirming both the returned shape and the source-vocabulary tag
(`function_report[...]["source"]` for Firecrawl-style; whatever tag
convention the plain-function sources use, per their own `_source`
column) are correct.

## 6. Run the automated tests - scoped to what you touched

```
poetry run pytest <the exact folder you scaffolded in> -q
poetry run pytest silver/silver_orchestrator -q   # only if contracts.py changed
```

Both should be green. Necessary, not sufficient - green tests confirm
internal consistency, not that the output looks right to a human. Do not
stop here.

## 7. Demonstrate the real output and get human approval - this concludes the task

Never skip this, regardless of how small the change looks:

1. Run the new function/class in isolation (not the full pipeline)
   against at least: that folder's existing sample fixture, a
   context-override case if it has one, and an empty/negative case. A
   small standalone script works:
   ```python
   # adjust the import to wherever you actually scaffolded this in step 1
   from silver.<source>.<...>.datapoints.<name> import <function_or_class>

   # feed it that folder's own sample fixture / a representative raw record
   ...
   print("value:", repr(result))
   print("source tag:", ...)  # whatever this folder's own convention is
   ```
   Run with `PYTHONPATH="$(pwd)" poetry run python <script path>` from the
   repo root (a standalone script outside `silver/` doesn't get the repo
   root on `sys.path` the way pytest does).
2. Paste the actual printed output into the chat, verbatim - not a
   paraphrase or a claim that it "looks right."
3. Wait for explicit approval before considering the datapoint done. If
   the output looks wrong, fix it and repeat this step - a passing test
   suite alone is never sufficient evidence.
