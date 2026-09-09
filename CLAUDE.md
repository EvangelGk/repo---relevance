# CLAUDE.md

Context and working agreements for Claude Code in this repository.

## What this repo is

The Silver layer of a company-enrichment pipeline. A future full "Artemis"
orchestrator layer is referenced conceptually in code comments but doesn't
exist here yet. `bronze/` held nothing until the 2026-09-08 addition below
gave it its first real piece (`bronze/clay/`).

## Layout

```
repo root/
  app.py                          - Streamlit UI, SilverOrchestrator-backed
  pyproject.toml / poetry.toml     - dependency + venv config (see Environment)
  client_context/                 - ClientContext (interpreted-brief/ICP spec), Artemis step 1
    schema.py                     - ClientContext dataclass, load/validate, Clay enum constants
    clients/                      - one JSON file per client context
  bronze/                         - Artemis step 3 (pull from source)
    clay/                         - Clay public API: company search driven by a ClientContext
      _http.py                    - stdlib-only authenticated client (CLAY_PUBLIC_API_KEY)
      query_builder.py            - ClientContext -> Clay search-query-language string
      search.py                   - run_company_search(): query-mode create + paginated run
    firecrawl/                    - PLACEHOLDER: direct Firecrawl.dev scrape calls, no Clay relay
      _http.py                    - stdlib-only authenticated client (FIRECRAWL_API_KEY)
      scrape.py                   - scrape_url(): -> {markdown, source_url, title, status_code}
    apify/                        - PLACEHOLDER: direct Apify actor calls, no Clay relay
      _http.py                    - stdlib-only authenticated client (APIFY_API_TOKEN)
      run_actor.py                - run_actor(): sync actor run -> raw dataset items, unflattened
    prospeo/                      - PLACEHOLDER: direct Prospeo calls, primary people source
      _http.py                    - stdlib-only authenticated client (PROSPEO_API_KEY, X-KEY header)
      search_person.py            - search_person(): job-title-filtered discovery, unrevealed contacts
      enrich_person.py            - enrich_person(): separate, costlier reveal of email/mobile
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

## Secrets management (SOPS + age)

Real API keys never go into git as plaintext. The repo tracks an
encrypted `.env.enc`; each developer decrypts their own local `.env` from
it (gitignored, never committed) using their personal age key.

**One-time per-developer setup:** run `/add-secrets-recipient` - it
installs `sops`/`age` via winget if you don't have them, generates your
keypair and shows it to you **exactly once** (it never writes the private
key to disk itself - copy it and save it yourself, wherever you trust;
see the skill for why and where `sops` will later expect to find it), and
adds your public key to `.sops.yaml` for you. It cannot re-encrypt
`.env.enc` itself (that needs plaintext access, which only an existing
recipient has) - after it runs, the admin still has to pull the updated
`.sops.yaml` and re-encrypt (see below). Once that's done, run
`/decrypt-secrets` to get your own working `.env`.

**Day-to-day:** `make` is **not guaranteed to be installed** (it isn't,
by default, on a plain Windows box - confirmed the hard way while
building this). If you have it, `make secrets-decrypt` /
`make secrets-encrypt` are shorthand for the two commands below; if not,
run the `sops` commands directly:
- Decrypt `.env.enc` into a local `.env` (after `poetry install` - see
  below - and any time `.env.enc` changes upstream):
  ```
  sops --input-type dotenv --output-type dotenv -d .env.enc > .env
  ```
- Re-encrypt your local `.env` into `.env.enc`, for whoever is updating
  the shared secrets (only do this with a real, complete `.env` - it
  overwrites `.env.enc` for the whole team once committed):
  ```
  sops --input-type dotenv --output-type dotenv -e .env > .env.enc
  ```
- The Makefile targets fail with a clear error if `sops` isn't on `PATH`;
  the raw commands above just error directly from `sops` itself.
- **`.env` stays gitignored and is never committed** - only `.env.enc` is
  the tracked, shareable artifact. `.env.example` (the plaintext template
  of expected keys with placeholder values) is unaffected by any of this.

**On `poetry install`:** Poetry has no clean, dependency-free post-install
hook (that requires a third-party plugin, which felt like the wrong
tradeoff just for this), so decrypting is **not** wired to run
automatically. Run `/decrypt-secrets` (or `make secrets-decrypt`/the raw
`sops` command above) manually right after `poetry
install` on a fresh checkout.

**Gotchas found live, not hypothetical (2026-09-09):** the first
`.env.enc` committed to this repo was silently broken - `sops -d` failed
with `Could not unmarshal input data`, not a key-mismatch error. Root
causes, both now fixed in `.sops.yaml`/`Makefile`:
- `input_type`/`output_type` are **not real `creation_rules` keys** -
  sops only accepts them as CLI flags (`--input-type`/`--output-type`).
  They sat in `.sops.yaml` as silently-ignored no-ops, so sops fell back
  to guessing format from each filename's extension - `.env` on encrypt
  (dotenv), `.enc` on decrypt (not a recognized extension, falls back to
  a JSON-shaped guess) - two different formats that can never read each
  other back. Fixed by pinning `--input-type dotenv --output-type dotenv`
  explicitly in both Makefile targets and dropping the dead keys from
  `.sops.yaml`.
- Windows gotcha: this repo's `sops` (a native Windows binary) looks for
  the default age identity at `%AppData%\sops\age\keys.txt`
  (`C:\Users\<you>\AppData\Roaming\sops\age\keys.txt`), **not**
  `~/.config/sops/age/keys.txt` (the XDG path `age-keygen`'s own docs
  reference, and what you get on Linux/Mac). If decrypt fails with
  "failed to load age identities" despite a real key existing, either
  move/copy the key to the AppData path above or set
  `SOPS_AGE_KEY_FILE` to wherever it actually lives.
- Also stripped a UTF-8 BOM that had ended up at the start of
  `.sops.yaml` (harmless here since sops parsed the rest of the config
  fine either way, but worth knowing about if a future YAML tool run
  against this file complains about its first character).

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
- `/add-secrets-recipient` - self-service, one-shot flow for a new
  teammate to generate their own age keypair (installing `sops`/`age` via
  winget if missing), see it exactly once to save themselves, and get
  added to `.sops.yaml`, with no manual YAML editing. Doesn't decrypt or
  re-encrypt anything - the admin still has to re-encrypt afterwards (see
  "Secrets management (SOPS + age)" above).
- `/decrypt-secrets` - decrypt `.env.enc` into a local `.env`, gated on
  already being a listed recipient in `.sops.yaml`. Points at
  `/add-secrets-recipient` if it isn't set up yet.

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

## 2026-09-08 addition: client_context/ + bronze/clay/ (Clay company search)

New scope beyond what this file described until today - Artemis steps 1
("interpret brief") and 3 ("pull from source"), which ARTEMIS_CONTEXT.md
had previously scoped as out of bounds for this repo (it only prototyped
steps 5-6). Added at explicit user direction while exploring Clay's public
developer API from the terminal; not a silent scope drift.

- `client_context/schema.py` - `ClientContext`, a frozen dataclass for one
  client's interpreted ICP, loaded from a JSON file via
  `load_client_context()` / `list_client_contexts()`. Field names mirror
  Clay's own company-search field catalog on purpose (see the module
  docstring) so a context file's shape stays legible against Clay's docs.
  `industries` and `company_size_buckets` are validated at load time
  against `CLAY_INDUSTRIES`/`CLAY_COMPANY_SIZE_BUCKETS`, both extracted
  verbatim from Clay's live `GET /search/query-mode/reference` on
  2026-09-08 (not hand-typed) - re-pull and regenerate if Clay's enum
  values ever change. `hq_countries`/`hq_cities` are deliberately NOT
  enum-validated (Clay's country enum is ~250 entries; duplicating it here
  would just be a second copy to drift out of sync with Clay's own list).
- `bronze/clay/_http.py` - stdlib-`urllib`-only client (no `requests`
  dependency added; would have meant a poetry lock/install round-trip
  before any of this could be tried). Reads `CLAY_PUBLIC_API_KEY` from the
  environment, falling back to a hand-rolled `.env` parse anchored to this
  module's own file location - the same "anchor to module location, not
  caller's cwd" pattern `dead_letter.py`/`drift.py` already use.
- `bronze/clay/query_builder.py` - `build_company_query(ClientContext)`
  builds a Clay search-query-language string. Every clause is grounded in
  a specific rule from Clay's live query-mode reference doc (cited inline)
  - nothing here invents Clay syntax for a case the reference doesn't
  confirm.
- `bronze/clay/search.py` - `run_company_search()`: the two-step Clay flow
  (`POST /search/query-mode` to compile, then repeated
  `POST /search/query-mode/{id}/run` calls paging on `has_more` until
  `ClientContext.limit` results are collected). Returns Clay's raw result
  dicts; merging them onto a Silver row (keyed by `domain_normalize`) is a
  separate, not-yet-built step.
- **Confirmed live against the real API, not just unit-tested**: a
  `ClientContext` round-tripped through `example_client.json` ->
  `build_company_query` -> `run_company_search` returned real companies
  (ignitetech.com, cloudeagle.ai, procol.ai) for a US/UK B2B-SaaS,
  51-500-employee, Software-Development-industry query.
- **Real bug found live, not hypothetical**: `exclude_domains` (->
  `clay.exclude_company_identifiers`) fails the **entire** search with
  HTTP 400 if even one domain in the list doesn't resolve to a company
  Clay knows about - not a partial result with the bad entry skipped. A
  real "already a customer" exclude list will eventually contain one
  stale/acquired/typo'd domain; documented as a live caveat in
  `query_builder.py` rather than silently worked around, since no
  known-good handling exists yet (catch `ClayAPIError` and retry without
  the offending domain, or pre-verify every domain resolves).
- `pyproject.toml`'s `testpaths` extended from `["silver"]` to
  `["silver", "client_context", "bronze"]` so `poetry run pytest` actually
  discovers the new test suites - previously they'd have silently not run.
- `.env` / `.env.example` added (gitignored / committed template
  respectively) for `CLAY_PUBLIC_API_KEY` and `CLAY_WORKSPACE_ID`.

## 2026-09-08 addition: bronze/firecrawl/ + bronze/apify/ (placeholders)

Decided, in the same terminal conversation as the client_context/bronze.clay
addition above: Firecrawl and Apify are single-vendor, no-waterfall calls
(unlike a Clay-managed enrichment, there's no second provider to fail over
to), so they're called **directly** from Python - no Clay relay. Routing
either through a Clay function was found to add a real storage ceiling for
zero benefit (a Clay basic/formula column caps at 8,000 characters, an
action/HTTP-API column at 200KB - a long scraped page or an Apify actor's
full item array can exceed both, and the Public API can't return more than
what Clay actually stored, since truncation happens at write time, not at
read time).

- `bronze/firecrawl/_http.py` + `scrape.py` - `scrape_url()` calls
  Firecrawl.dev's `/scrape` directly and returns `{markdown, source_url,
  title, status_code}`. `source_url` is `data.metadata.sourceURL` - exactly
  the `context["source_url"]` input `domain_normalize` requires, so the
  result can be handed straight to `Firecrawl.run_all()`.
- `bronze/apify/_http.py` + `run_actor.py` - `run_actor()` calls Apify's
  `run-sync-get-dataset-items` convenience endpoint (one call: run an
  actor synchronously, get its dataset items back directly, no separate
  poll) and returns the raw item dicts, deliberately unflattened - a
  different actor returns a different shape, so no per-actor field logic
  belongs in this module. `silver/apify/` (still empty) is the reserved
  slot for that normalization, mirroring how `silver/firecrawl/datapoints/
  *.py` turns raw markdown into typed fields.
- **Genuinely placeholders, not fully wired in yet**: neither module is
  called from `SilverOrchestrator` or anywhere else. Apify's async
  run + poll + fetch-dataset flow (for an actor that outruns the 300s
  synchronous window) isn't implemented. Which actor(s) this repo will
  actually use isn't decided - `run_actor()` takes `actor_id` as a
  parameter rather than hardcoding one.
- `.env` / `.env.example` extended with `FIRECRAWL_API_KEY` and
  `APIFY_API_TOKEN` (both `Authorization: Bearer <...>`, confirmed live
  against each vendor's docs 2026-09-08).
- **Both keys live-tested successfully once populated**: `scrape_url` on
  `https://firecrawl.dev` returned a real 200 with ~29.6k characters of
  markdown; `run_actor("apify~hello-world", ...)` returned
  `[{"message": "Hello world!"}]` after the token was independently
  confirmed via `GET /users/me`. Gotcha for later: Apify's store page
  shows actor paths with a slash (`apify/hello-world`) but the API needs
  the tilde form (`apify~hello-world`) - `run_actor()`'s docstring already
  documents this correctly.

## 2026-09-08 addition: bronze/prospeo/ (placeholder) - primary people source

Decided in the same terminal conversation: unlike Firecrawl/Apify,
Prospeo's Search Person endpoint is a genuine proprietary discovery
dataset (200M+ contacts, 30+ filters - job title, seniority, company,
location), the same category as Clay's own company search rather than a
single-utility relay. It's called directly because Clay's own native
Prospeo integration only covers Prospeo's *enrichment* endpoints (billed
through Clay's credits), not this separate Search Person product - so
using Search Person as a people source needs its own account regardless.

- Auth confirmed live against prospeo.io/api-docs, 2026-09-08: base URL
  `https://api.prospeo.io`, a plain `X-KEY` header - not `Authorization:
  Bearer` like Firecrawl/Apify/most REST APIs, so don't assume the same
  shape when adding a fourth vendor.
- `search_person.py` - job-title include/exclude + `match_mode` (Prospeo's
  filtering is list-based, NOT literal boolean AND/OR/NOT operator
  syntax, despite reading that way colloquially). Deliberately does not
  reveal email/mobile - those fields come back present but masked.
- `enrich_person.py` - the separate, costlier call (1 credit/email,
  10 credits/mobile) that actually reveals contact details. Split into two
  modules on purpose: `search_person()` is cheap (1 credit per successful
  search, up to 25 results, free within a 30-day dedup window) and should
  be gated on before ever calling `enrich_person()` - the same
  "gate before you spend" discipline `triage.py` already applies in front
  of Firecrawl. The gate itself isn't built yet; this is still a
  placeholder.
- Likely (not confirmed) explanation for an observed dashboard behavior:
  Prospeo's web UI "search and download" flow appears to silently call an
  enrich-equivalent step per row before export, since a downloaded CSV
  shows revealed fields the Search Person API alone never returns. Not
  documented anywhere Clay-adjacent; verify against the account's own
  credit/usage history, not this comment, before relying on it.
- `.env` / `.env.example` extended with `PROSPEO_API_KEY`.
