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
- **The "Run Firecrawl" button starts disabled** and only becomes enabled
  after the rerun that follows the blur above. Poll for it instead of a
  fixed sleep:
  ```python
  page.wait_for_function(
      """() => {
          const btns = [...document.querySelectorAll('button')]
              .filter(b => b.innerText.includes('Run Firecrawl'));
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
  small waits between calls).
- **Two "download" buttons exist on the result table** - the dataframe's
  built-in toolbar download icon, and the app's own `st.download_button`.
  Target the real one specifically:
  `page.get_by_test_id("stDownloadButton").get_by_role("button")` - a bare
  `get_by_role("button", name="Download as CSV")` matches both and raises a
  strict-mode violation.
- **Always check `console --errors` equivalent before declaring success:**
  ```python
  errors = []
  page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
  ```
  A Styler/pandas error can render an empty-looking table with no visible
  banner - the console is where it shows up.

## What to verify on the golden path

1. Paste `silver/firecrawl/tests/sample_input.md` -> click Run Firecrawl ->
   a result table appears with `quality_score`, `is_valid_row`,
   `rejection_reasons` as the first three columns and
   `raw_markdown_input` last; `is_valid_row` is checked/True; the row is
   NOT pink-highlighted.
2. Paste a lottery-shaped snippet (e.g. `"## Tonight's Draw Results\n\nThe
   winning numbers for tonight's lottery jackpot were 4, 8, 15, 16, 23,
   42.\n"`) -> re-run -> `is_valid_row` is False, `quality_score` is 0.0, a
   "Rejected: [...]" warning banner appears, and the row IS
   pink-highlighted.
3. Click "Download as CSV" (via the `stDownloadButton` selector above) and
   read the file back with `pandas.read_csv` - confirm the same column
   order survives (styling doesn't survive to CSV, the column order does).

## Clean up after

Manual UI runs write real entries into
`silver/silver_orchestrator/data/dead_letter.jsonl` and
`quality_history.jsonl` (SilverOrchestrator's default paths). Delete these
after a verification session so they don't pollute real drift history for
the next run:

```bash
rm -f silver/silver_orchestrator/data/dead_letter.jsonl silver/silver_orchestrator/data/quality_history.jsonl
```
