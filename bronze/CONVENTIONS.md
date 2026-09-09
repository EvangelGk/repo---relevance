# Bronze intermediate-CSV conventions

How a bronze-level pull (Clay, Firecrawl, Apify, Prospeo) turns into an
intermediate CSV under `client_context/clients/<client_id>/processed/`,
before anything reaches Silver. Written down after several rounds of
"not quite that shape" while building `bronze/pipeline.py`'s Firecrawl
step for the `trial-fintech-us-uk` client (rule 6's file-naming was
revised once more, 2026-09-09, once the Apify step existed too and made
"Firecrawl and Apify are independent parallel branches over the same
company table, not a chain" concrete) - the rules below are what that
back-and-forth converged on, made explicit so the next bronze module
(`prospeo`, and any future source) doesn't have to rediscover them.

1. **Primary key: `clay_company_id`.** Every intermediate CSV in a
   client's `processed/` folder is keyed by it - Clay's own unique company
   ID, already present on every row Clay's search returns
   (`bronze/clay/search.py`). Nothing here is joined by `domain` alone
   (domains can get re-normalized/renamed) or by row order.

2. **A small identity spine rides along as real columns, not JSON:**
   `clay_company_id`, `name`, `domain`, `linkedin_url`. These four are
   cheap, stable, and needed constantly for filtering/joining/skimming a
   CSV by eye - burying them inside a JSON blob just means re-parsing
   every row to filter by domain. Nothing else from the original company
   record (`size`, `type`, `country`, `industry`, `location`,
   `description`, `annual_revenue`, `total_funding_amount_range_usd`, ...)
   gets this treatment - see rule 4.

3. **Everything a bronze function itself produces goes into exactly one
   JSON column, unflattened**, named `<source>_bronze_json` (e.g.
   `apify_bronze_json` in `<client_id>_apify_bronze.csv`, mirroring that
   file's own `<client_id>_<source>_bronze.csv` name - see rule 6). Never
   split one function's output across
   multiple columns, and never duplicate a field both as its own column
   *and* inside the JSON blob (e.g. a `scrape_status` column next to a
   JSON blob that already has `"scrape_status"` in it) - pick one home per
   field. This mirrors the "raw dataset items, unflattened" rule
   `bronze/apify/run_actor.py` already follows, generalized to every
   bronze source.

4. **Intermediate steps don't carry full company metadata - only the
   primary key.** A step's output is `{identity spine} + {that step's own
   JSON blob}`, nothing more. The rest of a company's original fields
   (industry, description, funding range, ...) live in the client's
   source company list (`<client_id>_company_table_v1.csv` - see rule 6)
   and get joined back in by `clay_company_id` at the *final* merge step -
   not dragged through every intermediate CSV along the way. Fewer columns
   in the middle means a pipeline change (adding a fifth bronze source,
   say) never has to touch every other step's schema.

5. **A bronze function's input is exactly what it needs, not a whole
   row.** `scrape_url()` needs a URL (built from `domain`); it doesn't need
   `industry` or `annual_revenue` passed in to ignore. The caller builds
   that minimal input from the identity spine, calls the function, and
   merges the result back onto `clay_company_id` - the function itself
   never sees, and doesn't need, the rest of the row.

6. **File naming, revised 2026-09-09:** one file per pipeline step,
   `client_context/clients/<client_id>/processed/<client_id>_<step>.csv` -
   the client id prefixes every filename (not just the folder path), so a
   file is self-identifying if it's ever copied out of its `processed/`
   folder. Concretely, for client `trial-fintech-us-uk`:
   - `trial-fintech-us-uk_company_table_v1.csv` - the source company list
     (rule 4), versioned (`_v1`) because re-running Clay's search or
     hand-editing the ICP later produces a new company set, not a patch to
     the old one.
   - `trial-fintech-us-uk_firecrawl_bronze.csv` - the Firecrawl bronze step.
   - `trial-fintech-us-uk_apify_bronze.csv` - the Apify bronze step.
   Firecrawl's and Apify's bronze steps both read the *same*
   `<client_id>_company_table_v1.csv` and run independently (each keyed
   back onto it by `clay_company_id` in its own output) - they're parallel
   branches over the same input, not chained to each other, and get merged
   together only later, downstream of both. No `.tmp`/`.v2`/`.v3` suffixes
   in what's actually kept around; those only ever exist transiently when
   a prior version of the file is locked open elsewhere (e.g. in Excel).

Not covered here: Silver's own output schema (`DATAPOINT_CONTRACTS` in
`silver/silver_orchestrator/contracts.py`) - that's a different, later
stage with its own required/optional rules and is already well-specified
there. These conventions are about the bronze-pull -> intermediate-CSV
stage that happens *before* Silver ever runs.
