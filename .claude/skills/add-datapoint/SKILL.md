---
name: add-datapoint
description: Scaffold a new Firecrawl datapoint extractor (base class subclass, self._last_source wiring, registration) plus its DatapointContract entry and a smoke test, following this repo's established datapoint pattern.
---

# Add a new Firecrawl datapoint function

Before writing code, confirm with the user (or infer from their request):
- The function's snake_case name (this becomes the filename, the class
  `name` attribute, and the dict key in every row).
- What it extracts, and from where: markdown prose only, `context` only, or
  both (context taking priority, markdown as fallback - the
  `tech_stack_normalize` / `company_entity_resolve` pattern).
- What "empty" looks like for it (`None`? `[]`? `{}`?) and whether that's
  actually common on real pages (most datapoints are legitimately
  empty often - see `/review-contract`).

## 1. Create `silver/firecrawl/datapoints/<name>.py`

- Subclass `DataPointExtractor` from `..base`.
- `name = "<name>"` (must match the filename).
- Implement `extract(self, markdown: str, context: dict)`.
- Set `self._last_source` at **every** return point:
  - Non-empty from `context` -> `self._last_source = "context"`.
  - Non-empty from markdown scanning -> `"markdown"` (or a more specific
    label already in use elsewhere if it fits - `"markdown_fallback"`,
    `"hreflang"`, `"html"` - don't invent a new vocabulary word without a
    reason).
  - Empty/nothing found -> `self._last_source = None`.
- Return `None` / `[]` / `{}` for "nothing found" rather than a dict of all
  the sub-keys set to `None` - `Firecrawl._collapse_if_blank` already
  normalizes an all-blank dict to `None` downstream, so don't hand-roll that.

**Reference implementations to copy the shape from:**
- `experience_signal_extract.py` - simplest template: markdown-only,
  single source, always returns a dict (never `None`).
- `tech_stack_normalize.py` or `company_entity_resolve.py` - template for a
  function with a real context-vs-markdown fork.
- `date_normalize.py` or `regulatory_event_classify.py` - template for a
  function that already returns a `DataPointResult(value=..., source=...)`
  wrapper (needed only when the *per-field* `_source` column in `row` also
  matters, not just `self._last_source` for `function_report`).

## 2. Register it

Add one import line to `silver/firecrawl/datapoints/__init__.py`. Position
matters: import order is execution order, since later extractors can read
earlier ones' output out of `context[<name>]`. Put it after anything it
needs to read, before anything that needs to read it.

## 3. Add a `DatapointContract` entry

In `silver/silver_orchestrator/contracts.py`'s `DATAPOINT_CONTRACTS` dict:
- `required=False` in the overwhelming majority of cases. Only flip to
  `True` after checking with the user - today it's reserved for
  `domain_normalize` and `company_entity_resolve` (join-key-critical
  fields).
- `null_tolerance_pct` - estimate honestly from how often this signal
  would appear on a typical B2B company page, and leave a trailing comment
  explaining the number, matching the existing entries' style.
- `source_priority` - an ordered tuple, best source first, matching
  exactly the `self._last_source` vocabulary this function can emit.
- `enum_values` - only if the value is a controlled vocabulary (see
  `regulatory_event_classify` for the flat-tuple case, `business_model` for
  the nested tuple-of-tuples exception - read the dataclass docstring
  before copying that pattern).

Full checklist for the contract itself: `/review-contract`.

## 4. Wire it into the Streamlit UI (`app.py`) - always, not optionally

`app.py`'s result table needs no change to show the new datapoint - it's
built dynamically from `orchestrator.process_page()`'s row dict
(`_flatten_row`/`_reorder_columns`), so the new column appears
automatically. But do these two checks every time, not just when it's
convenient:

- **If the new extractor reads a context override key** (like
  `tech_stack_normalize`'s `detected_tools`, or `company_description_extract`'s
  `company_description`), add a matching input widget to the "Optional
  context overrides" `st.expander(...)` in `app.py`, and add that key to
  the `overrides` dict built on button click. Skipping this leaves the
  context path fully wired in code but untestable through the UI - don't
  let "the markdown fallback path works" stand in for actually checking
  the override path a human would use.
- **If the new extractor is markdown-only with no context override**
  (like `experience_signal_extract`), there is nothing to add to `app.py` -
  say that explicitly in your summary rather than silently skipping the
  step, so it's clear you checked rather than forgot.

Adding an override field is itself a UI-logic change, which is exactly
what the `/run-streamlit-ui` working agreement in `CLAUDE.md` calls out as
worth the Playwright drive-through (unlike a pure extraction-logic change,
which doesn't need it) - use it if you want to confirm the new field
actually renders and gets passed through, on top of the manual
demonstration in step 7.

## 5. Add tests

In `silver/firecrawl/tests/test_firecrawl.py`, add at least:
- A happy-path case against `sample_input.md` (or a purpose-built inline
  snippet, if the sample fixture doesn't exercise this signal), reading
  `Firecrawl().run_all(...)["row"]["<name>"]`.
- An empty/negative case, confirming it collapses to the right "nothing
  found" shape and that `function_report["<name>"]["source"]` is `None`.

## 6. Run the automated tests

```
poetry run pytest silver/firecrawl -q
poetry run pytest silver/silver_orchestrator -q   # contracts.py changed too
```

Both should be green. This is necessary but **not sufficient** - green tests
confirm the assertions you wrote are internally consistent, not that the
extractor's actual output looks right to a human. Do not stop here.

## 7. Demonstrate the real output and get human approval - this is what concludes the task

The task is not done when tests pass. It is done when a human has seen the
new extractor's real output on real markdown and said it's good. Every
time, regardless of how small the change looks:

1. Run **only the new extractor class** in isolation (not the full
   `Firecrawl` pipeline, so the output isn't buried among all the other
   columns) against at least: `silver/firecrawl/tests/sample_input.md`, a
   context-override case if the function has one, and an empty/negative
   case. A small standalone script works well:
   ```python
   from silver.firecrawl.datapoints.<name> import <ClassName>

   markdown = open("silver/firecrawl/tests/sample_input.md", encoding="utf-8").read()
   extractor = <ClassName>()
   result = extractor.extract(markdown, {})
   print("value:", repr(result))
   print("_last_source:", extractor._last_source)
   ```
   Run it with `poetry run python <script path>`. Note: a standalone script
   outside `silver/` doesn't get the repo root on `sys.path` the way pytest
   does (`pythonpath = ["."]` in `pyproject.toml` only applies to pytest) -
   prefix the command with `PYTHONPATH="$(pwd)"` (from the repo root) or
   you'll hit `ModuleNotFoundError: No module named 'silver'`.
2. Paste the actual printed output into the chat, verbatim - not a
   paraphrase or a claim that it "looks right." The human needs to see the
   real value and the real `_last_source` for each case.
3. Wait for explicit approval before considering the datapoint done. If the
   output looks wrong, fix the extractor and repeat this step - don't move
   on with a passing test suite alone as your evidence.
