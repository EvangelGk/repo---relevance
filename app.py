"""Streamlit test harness for the Silver layer: paste (or upload) cleaned
markdown, hit "Run Firecrawl", get one row with a column per datapoint plus
the audit signal (quality_score, is_valid_row, rejection_reasons) up front
and the raw markdown last.

This runs everything through SilverOrchestrator rather than calling
Firecrawl directly - Firecrawl is pure execution (runs all 17 datapoint
functions, reports what happened) and never decides whether a page was
worth running or whether its output is good enough to trust. That decision
(is_company_profile, schema_gate, quality_score, drift) is
SilverOrchestrator's job, so a rejected or low-quality result is visible
right in this table instead of silently looking like any other row.

Run with: streamlit run app.py
"""
import json

import pandas as pd
import streamlit as st

from silver.firecrawl import Firecrawl
from silver.silver_orchestrator.orchestrator import SilverOrchestrator

_FLAG_COLUMNS = ["quality_score", "is_valid_row", "rejection_reasons"]
_LAST_COLUMN = "raw_markdown_input"
_INVALID_ROW_HIGHLIGHT = "background-color: #fbdcdc"


@st.cache_resource
def get_orchestrator() -> SilverOrchestrator:
    return SilverOrchestrator(Firecrawl())


def _flatten_row(row: dict) -> dict:
    """JSON-encode every non-scalar value so the row fits in a table cell -
    same flattening Firecrawl.run_all_as_dataframe() used to do, now applied
    to SilverOrchestrator's row instead."""
    return {
        key: value if isinstance(value, (str, int, float, bool, type(None))) else json.dumps(value, default=str)
        for key, value in row.items()
    }


def _reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Audit signal first, raw markdown last, everything else in between -
    so the reviewer sees whether to trust a row before scrolling through 17
    datapoint columns to find out."""
    flag_cols = [c for c in _FLAG_COLUMNS if c in df.columns]
    last_col = [_LAST_COLUMN] if _LAST_COLUMN in df.columns else []
    middle_cols = [c for c in df.columns if c not in flag_cols and c not in last_col]
    return df[flag_cols + middle_cols + last_col]


def _highlight_invalid_rows(row: pd.Series):
    style = _INVALID_ROW_HIGHLIGHT if not row.get("is_valid_row", True) else ""
    return [style] * len(row)


def _sort_valid_first(df: pd.DataFrame) -> pd.DataFrame:
    """Same stable valid-first ordering as SilverOrchestrator.process_batch,
    kept here too so a future batch-upload path and this single-row path
    always agree on how rows are ordered."""
    if df.empty or "is_valid_row" not in df.columns:
        return df
    sort_key = (~df["is_valid_row"].astype(bool)).to_numpy()
    return df.iloc[sort_key.argsort(kind="stable")].reset_index(drop=True)


orchestrator = get_orchestrator()

st.set_page_config(page_title="Firecrawl", layout="wide")
st.title("Firecrawl")
st.caption("Paste or upload cleaned markdown from a scraped page, run every datapoint extractor at once.")

uploaded_file = st.file_uploader("Upload a markdown file", type=["md", "markdown", "txt"])
pasted_markdown = st.text_area(
    "Or paste cleaned markdown", height=350, placeholder="Paste Firecrawl markdown here..."
)
markdown_input = uploaded_file.read().decode("utf-8") if uploaded_file is not None else pasted_markdown

with st.expander("Optional context overrides"):
    st.caption("Fill in whatever the page itself can't supply (blank = skipped).")
    col1, col2 = st.columns(2)
    with col1:
        source_url = st.text_input("source_url")
        company_name = st.text_input("company_name")
        company_description = st.text_input("company_description")
        parent_guess = st.text_input("parent_guess")
        entity_id = st.text_input("entity_id")
        raw_date = st.text_input("raw_date")
        regulatory_event_text = st.text_input("regulatory_event_text")
    with col2:
        timeseries_field = st.text_input("timeseries_field", value="numberOfEmployees")
        timeseries_value = st.text_input("timeseries_value")
        snapshot_date = st.text_input("snapshot_date")
        last_enriched_date = st.text_input("last_enriched_date")
        re_verification_due_date = st.text_input("re_verification_due_date")

run_clicked = st.button("Run Firecrawl", type="primary", disabled=not markdown_input.strip())

if run_clicked:
    overrides = {
        "source_url": source_url,
        "company_name": company_name,
        "company_description": company_description,
        "parent_guess": parent_guess,
        "entity_id": entity_id,
        "raw_date": raw_date,
        "regulatory_event_text": regulatory_event_text,
        "timeseries_field": timeseries_field,
        "timeseries_value": timeseries_value,
        "snapshot_date": snapshot_date,
        "last_enriched_date": last_enriched_date,
        "re_verification_due_date": re_verification_due_date,
    }
    overrides = {k: v for k, v in overrides.items() if v}

    row = orchestrator.process_page(markdown_input, overrides)
    st.session_state["last_result"] = _flatten_row(row)

if "last_result" in st.session_state:
    row = st.session_state["last_result"]
    df = pd.DataFrame([row])
    df = _reorder_columns(df)
    df = _sort_valid_first(df)

    st.subheader("Result")
    if not bool(df.iloc[0]["is_valid_row"]):
        st.warning(f"Rejected: {df.iloc[0]['rejection_reasons']}")
    styled = df.style.apply(_highlight_invalid_rows, axis=1)
    st.dataframe(styled, use_container_width=True)

    st.download_button(
        "Download as CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="firecrawl_result.csv",
        mime="text/csv",
    )
    with st.expander("Raw JSON (excludes raw_markdown_input)"):
        st.json({k: v for k, v in row.items() if k != _LAST_COLUMN})
