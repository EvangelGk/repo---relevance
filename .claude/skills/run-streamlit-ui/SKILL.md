---
name: run-streamlit-ui
description: Launch this repo's Streamlit app (app.py) and drive it headlessly with Playwright to verify a change - the exact recipe for this app's Streamlit quirks (controlled-input blur, disabled-button race, canvas-based dataframe grid).
---

# Running and driving the Firecrawl / SilverOrchestrator Streamlit UI

Only do this for changes that actually touch UI rendering or logic
(`app.py`, or a change to `SilverOrchestrator`/`Firecrawl` output shape that
the UI displays). For everything else, `poetry run pytest` is enough - see
CLAUDE.md's working agreements.

There is no `chromium-cli` in this environment; drive the browser with
Python Playwright instead, through the project's own venv (`poetry run
python <script>.py`).

## Launch

```bash
lsof -ti:8501 -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null   # free the port first
nohup poetry run streamlit run app.py --server.headless true --server.port 8501 > /tmp/streamlit.log 2>&1 &
timeout 30 bash -c 'until curl -sf http://localhost:8501 >/dev/null; do sleep 1; done'
```

Stop with the same `lsof -ti:8501 ... | xargs -r kill` line when done -
`nohup ... &`'s `$!` is the shell wrapper, not reliable for a clean kill.

One-time setup if the browser binary isn't installed yet:
`poetry run playwright install chromium`.

## Drive it

Write a small script and run it with `poetry run python <script>.py`. Use
`playwright.sync_api.sync_playwright()`. Gotchas specific to this app,
learned the hard way - don't rediscover these:

- **Streamlit text areas only rerun on blur or Ctrl+Enter.** After
  `.fill(...)`, call `.press("Tab")` (or click elsewhere) - `fill()` alone
  sets the value but never fires Streamlit's `on_change` rerun, so anything
  gated on the new value (like the Run button's disabled state) won't
  update.
- **The "Run audit" button starts disabled** (Firecrawl Audit tab) and
  only becomes enabled after the rerun that follows the blur above. Poll
  for it instead of a fixed sleep:
  ```python
  page.wait_for_function(
      """() => {
          const btns = [...document.querySelectorAll('button')]
              .filter(b => b.innerText.includes('Run audit'));
          return btns.length > 0 && !btns[0].disabled;
      }""",
      timeout=15000,
  )
  ```
- **`st.dataframe` renders via glide-data-grid, a `<canvas>`, not real DOM
  rows.** `page.inner_text("body")` will NOT show any cell values. To
  inspect table content, screenshot the grid element directly:
  ```python
  grid = page.locator('[data-testid="stDataFrame"]').first
  grid.scroll_into_view_if_needed()
  grid.screenshot(path="table.png")
  ```
  To see columns beyond the first screen, move the mouse over the grid and
  scroll it horizontally: `page.mouse.wheel(2000, 0)` (repeat a few times;
  small waits between calls). This still applies to the "Session history"
  table at the bottom of the Firecrawl Audit tab - the per-row result
  itself is no longer a dataframe at all (see below).
- **Only one download button exists now** - the per-row result display
  was redesigned (2026-09-08) into cards, not a `st.dataframe`, so there's
  no toolbar download icon to disambiguate from anymore. The app's own
  `st.download_button` is still the right target:
  `page.get_by_test_id("stDownloadButton").get_by_role("button")` - a bare
  `get_by_role("button", name="Download as CSV")` still works today too,
  but keep using the specific selector in case a dataframe-backed download
  control gets added back later.
- **Always check `console --errors` equivalent before declaring success:**
  ```python
  errors = []
  page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
  ```
  A Styler/pandas error can render an empty-looking table with no visible
  banner - the console is where it shows up.

## What to verify on the golden path

This app now has two tabs (`🔍 Firecrawl Audit`, `🧩 Unified Row
Preview`); the walkthrough below is for the first, which is where a
Firecrawl/SilverOrchestrator change actually needs verifying. The second
tab is an explicitly-labeled preview of `silver/company|people/`
connectors, not wired into any production pipeline - only drive it if
your change touches those connectors specifically.

1. Paste `silver/firecrawl/tests/sample_input.md` into the "Or paste
   cleaned markdown" box -> click "Run audit" -> a card header appears:
   quality score colored green (>=80), "✅ **Valid row**", crawl_status
   and content_integrity shown; no red rejection banner; no drift
   warning; the "Datapoints" section below shows grouped
   Identity/Descriptive/Signals expanders with a source-colored chip per
   field.
2. Paste a lottery-shaped snippet (e.g. `"## Tonight's Draw Results\n\nThe
   winning numbers for tonight's lottery jackpot were 4, 8, 15, 16, 23,
   42.\n"`) -> re-run -> score colored red, "🚫 **Rejected row**", and a
   red `st.error("Rejected - reasons: [...]")` banner. There is no
   row-highlighting concept in this app anymore (that was the old,
   retired single-table app) - don't look for it.
3. Click "Download as CSV" (via the `stDownloadButton` selector above) and
   read the file back with `pandas.read_csv` - confirm the same column
   order survives.

## Clean up after

Manual UI runs write real entries into
`silver/silver_orchestrator/data/dead_letter.jsonl` and
`quality_history.jsonl` (SilverOrchestrator's default paths). Delete these
after a verification session so they don't pollute real drift history for
the next run:

```bash
rm -f silver/silver_orchestrator/data/dead_letter.jsonl silver/silver_orchestrator/data/quality_history.jsonl
```
