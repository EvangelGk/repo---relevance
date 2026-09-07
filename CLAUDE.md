# CLAUDE.md

Context and working agreements for Claude Code in this repository.

## What this repo is

The Silver layer of a company-enrichment pipeline. `bronze/` and a future
full "Artemis" orchestrator layer are referenced conceptually in code
comments but don't exist here yet. Not currently a git repository.

## Layout

```
repo root/
  app.py                          - Streamlit UI, SilverOrchestrator-backed
  pyproject.toml / poetry.toml     - dependency + venv config (see Environment)
  bronze/                          - empty, future layer
  silver/
    apify/                        - empty, future source
    si_orchestrator/              - empty stub; unrelated to silver_orchestrator/ below
    firecrawl/                    - pure-execution datapoint extraction layer
      base.py                     - DataPointExtractor / REGISTRY / DataPointResult
      firecrawl.py                - Firecrawl.run_all() orchestrates all registered extractors
      _utils.py                   - shared markdown-parsing regex helpers
      datapoints/                 - one file per extractor (see DATAPOINT_CONTRACTS for the current count + conflict_check)
      tests/                      - pytest + fixtures (sample_input.md/.html, sample_context.json)
    silver_orchestrator/          - the Silver-layer quality gate in front of Firecrawl
      contracts.py                - DatapointContract dataclasses, DATAPOINT_CONTRACTS (source of truth)
      schema_gate.py              - hard-requirement validation (pandera + plain Python)
      quality_score.py            - 0-100 scoring off function_report
      dead_letter.py              - local JSONL audit trail for rejected rows
      drift.py                    - rolling-window empty-rate drift detection
      orchestrator.py             - SilverOrchestrator: is_company_profile gate + process_page/process_batch
      tests/
```

## Architecture

**Firecrawl (`silver/firecrawl/`) is pure execution.** It runs every
registered `DataPointExtractor` against whatever markdown it's given and
reports what happened - it never decides pass/fail and never skips itself.
`Firecrawl.run_all()` returns `{"row": {...}, "function_report": {...}}`:
- `row`: one key per extractor (`raw_markdown_input`, `run_timestamp`, plus
  all 18 extractor outputs) - the flat shape that goes into a CSV.
  `run_all_as_dataframe()` uses only this half.
- `function_report`: for each **datapoint function in DATAPOINT_CONTRACTS** (excludes
  `conflict_check`, which is a QA cross-check pass, not a datapoint) -
  `{"ran": bool, "is_empty": bool, "source": str | None}`.

Extractors auto-register into `base.REGISTRY` via `__init_subclass__` -
`datapoints/__init__.py`'s import order IS execution order, since later
extractors read earlier ones' output out of `context`. Each extractor sets
`self._last_source` at every return point (vocabulary in use: `"context"`,
`"markdown"`, `"markdown_fallback"`, `"hreflang"`, `"html"`, or `None` when
empty) - see `base.py`'s docstring.

**SilverOrchestrator (`silver/silver_orchestrator/`) is the quality gate.**
`SilverOrchestrator.process_page()`:
1. Runs `is_company_profile()` (a heuristic gate - lottery/listicle
   language rejection, lives here, not in Firecrawl). If it fails, Firecrawl
   never runs at all - a stub row is returned instead (every datapoint key
   `None`, `is_valid_row=False`, `quality_score=0.0`).
2. Otherwise calls `firecrawl.run_all()`, validates the row via
   `schema_gate.evaluate_row()`, scores it via
   `quality_score.compute_quality_score()`, and records/checks drift per
   function via `drift.py`.
3. **Always returns a row - never `None`.** A rejected page is a
   visibly-flagged row (`is_valid_row`, `quality_score`,
   `rejection_reasons`, `drift_warnings`), not a silently dropped one.
   `dead_letter.jsonl` is a secondary audit trail written *alongside* the
   row, never instead of it.

`contracts.DATAPOINT_CONTRACTS` is the single source of truth:
`required=True` only for `domain_normalize` and `company_entity_resolve`'s
`company_id` sub-field (the two join-key-critical fields) - everything else
is `required=False` by design. Most functions are legitimately
empty on plenty of real pages; don't "fix" that by making them required.

## Environment

Dependency management is Poetry, self-contained to this repo - not your
machine's global Python:

- `poetry install` - creates `.venv` **inside the project**
  (`poetry.toml`'s `virtualenvs.in-project = true` travels with the repo,
  so this holds regardless of a developer's global Poetry config).
- `poetry run pytest` - full test suite (scoped to `silver/` via
  `[tool.pytest.ini_options]` in `pyproject.toml`; `pythonpath = ["."]` is
  there because `package-mode = false` means nothing is ever pip-installed,
  so pytest needs the repo root added to `sys.path` explicitly - `poetry
  run pytest` doesn't get the automatic cwd-insertion that `python -m
  pytest` gets).
- `poetry run streamlit run app.py` - the UI.
- `poetry run playwright install chromium` - one-time browser download,
  needed for `/run-streamlit-ui`.
- Add a runtime dependency with `poetry add <package>`; a dev/test-only one
  with `poetry add --group dev <package>`. There is no `requirements.txt`
  (retired in favor of `pyproject.toml` + `poetry.lock`) - don't recreate one.

## Working agreements (token/credit-conscious operation)

- **Prefer direct tools over agents.** Use Read/Grep/Glob directly for
  anything answerable in a couple of calls; only spawn an Explore/
  general-purpose agent for genuinely broad, open-ended discovery.
- **Batch independent reads** in one turn rather than sequential turns.
- **Don't re-verify what the harness already confirmed** - no re-reading a
  file right after Edit/Write just to check it worked.
- **Scope test runs.** `poetry run pytest silver/firecrawl -q` when only
  touching firecrawl, not the whole suite, unless doing a final
  cross-package check before calling something done.
- **Reserve the Streamlit+Playwright drive-through** (see
  `/run-streamlit-ui`) for changes that actually touch UI rendering/logic -
  skip it for comment edits, contract number tweaks, docstring changes.
- **Default to low/medium effort for `/code-review`** unless asked for
  more.
- **Reuse context already established in the conversation** instead of
  re-running `ls`/`find`/full-file exploration sweeps over territory
  that's already been mapped.
- **Ask permission once per scope, not per action** - within an approved
  task, don't pause for confirmation on each reversible sub-step.

## Available project skills

- `/add-datapoint` - scaffold a new Firecrawl extractor + contract entry +
  test, following the established 17-function pattern.
- `/run-streamlit-ui` - launch and drive the Streamlit app via headless
  Playwright, with this app's specific gotchas already worked out.
- `/review-contract` - checklist for adding/changing a `DatapointContract`
  entry in `contracts.py`.
- `/add-orchestrator-check` - scaffold a new hard-requirement, quality
  penalty, or drift rule consistently across `contracts.py`,
  `schema_gate.py`, `quality_score.py`, and their tests.
- `/explain-artemis-context` - explain how this repo fits into the
  broader Artemis/Hermes list-building pipeline, its current build
  state, and what's explicitly out of scope here, grounded in
  `ARTEMIS_CONTEXT.md`.
- `/explain-file` - deep, code-grounded explanation of one specific file
  or module (purpose, mechanism, inputs/outputs, failure modes, explicit
  exclusions) via a strict fixed-section template - for "how does this
  file work," not "how does this repo fit into Artemis."

## 2026-09-07 addition: crawl triage, content integrity, placeholder guard

Adapted from a B2B account-research crawl-extraction prompt shared via the
Cowork Project, scoped down to what this repo can actually ground in
markdown-only input. Built and tested directly in this repo (admin
sign-off intentionally skipped here - this is the sandbox repo, not the
shared monorepo those governance rules bind).

- `silver/silver_orchestrator/triage.py` - `classify_crawl_issue()` (a
  precedence-ladder gate: empty_response / parked_or_for_sale /
  under_construction / bot_challenge / login_required / cookie_wall /
  non_company_page / directory_or_aggregator / boilerplate_only / none)
  and `classify_content_integrity()` (genuine / placeholder_or_template /
  under_construction / unknown). Both run in
  `SilverOrchestrator.process_page()`, before `is_company_profile` and
  before `Firecrawl.run_all()`.
- Every row now also carries `crawl_issue`, `crawl_status`
  ("ok"/"partial"/"unusable"), `content_integrity`, and `schema_version`
  ("1.0" today - bump it if a field is ever added/removed/retyped).
- `schema_gate._check_no_placeholder_strings` - a new hard requirement:
  none of the contracted datapoint fields may hold a literal placeholder
  string ("N/A", "Unknown", "null", ...) instead of `None`/`[]`/`{}`.
- `GROUNDING_LAW.md` (new, `silver/silver_orchestrator/`) - the shared
  rule every datapoint function and both triage classifiers must follow:
  never derive a company fact from a domain, TLD, or detected page
  language.
- **Deliberately not ported**: `page_language` ISO-639 detection and the
  source prompt's "fabricated mock interface" rule - both assume a
  marketing-site scrape shape this repo's Apify-sourced fields don't have
  reason to need yet.
- **Behavior change, not just an addition**:
  `test_process_page_rejects_lottery_content` now expects
  `rejection_reasons == ["non_company_page"]`, not
  `["not_a_company_profile"]` - lottery content is caught by the new,
  earlier, more specific `classify_crawl_issue` ladder before
  `is_company_profile` ever runs.

## 2026-09-08 addition: datapoint pruning + domain_normalize/tech_stack/careers fixes

Prompted by real usage showing most-of-18 datapoint functions coming back
empty most of the time. Not every "usually empty" case has the same root
cause - some were genuine bugs, some were dead code, some were niche
signals correctly empty by design. Each got a different treatment instead
of a blanket "delete anything with a low hit rate":

- **Removed entirely** (structurally can't work, or too niche to matter):
  `structured_data_extract` (needed JSON-LD from a `<script>` tag - cleaned
  markdown never preserves this), `regulatory_event_classify` (near-zero
  hit rate outside regulated industries), `timeseries_snapshot` and
  `freshness` (both depended on inputs - `structured_data_extract`'s
  employee count, a re-enrichment history DB - that don't exist in this
  pipeline). `_utils.py`'s now-orphaned `extract_json_ld`,
  `JSON_LD_BLOCK_RE`, `JSON_FENCE_RE`, `HREFLANG_RE`, `LANG_ATTR_RE` were
  removed with them. `conflict_check.py`'s company-name check dropped its
  now-defunct `structured_data_extract` candidate.
- **Simplified** (kept the working half, cut the dead half):
  `site_locale_detect` no longer attempts `<html lang>`/`hreflang`
  detection (same "cleaned markdown doesn't preserve this" problem) -
  its markdown language-name/parenthetical-code scan is now the only path.
- **Fixed a real correctness bug, not just an emptiness one**:
  `domain_normalize` used to fall back to "the first link found anywhere
  on the page" when `context["source_url"]` wasn't given - this could
  confidently return a *wrong* domain (e.g. a footer's LinkedIn link),
  not just an empty one. It's now context["source_url"]-only;
  `company_entity_resolve` inherits the fix since it reads
  `domain_normalize`'s output. `source_priority` for both dropped their
  `"markdown"` entry accordingly.
- **Broadened for actual usefulness**: `tech_stack_normalize`'s vendor
  catalog grew from 18 names across 5 categories to ~75 across 13 -
  `mentioned_technologies` (markdown-only scanning) is the only signal
  this pipeline can produce today, since nothing feeds
  `context["detected_tools"]` yet, so its catalog size *is* its hit rate.
- **Rewrote for realistic input, not a hypothetical one**:
  `careers_page_parse`'s old strict format
  (`"TITLE — DEPT — LOCATION — Posted YYYY-MM-DD"`) almost never appears
  verbatim on a real scraped careers page, so it returned `[]` even ON
  genuine careers pages. It now tries that strict format first, then
  falls back to a looser per-bullet/heading parser (title required,
  department/location/posted_date extracted opportunistically and left
  `None` rather than failing the whole line) - scoped to a
  careers-shaped section only (broadened beyond "## Careers" to also
  match Jobs/Open Positions/Open Roles/We're Hiring/Join Us), never the
  whole page, so it can't misread an unrelated bullet list as job postings.
- Net effect: 18 registered extractors (17 + `company_description_extract`)
  down to 15 (14 real datapoints + `conflict_check`). Any hardcoded "17" or
  "18" count you see elsewhere in old comments is stale - the count is
  meant to be read off `contracts.DATAPOINT_CONTRACTS`, not memorized,
  since it will keep changing.
