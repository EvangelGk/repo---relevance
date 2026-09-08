"""Redesigned Streamlit UI - human-friendly visual auditing (Task 8 of the
2026-09-08 source-first restructure).

Additive only: this is a NEW file, `app.py` is untouched and still runs the
original UI exactly as before (`streamlit run app.py`). Run this one with:

    poetry run streamlit run app_v2.py

Two halves:
  1. "Firecrawl Audit" - the same SilverOrchestrator-backed pipeline
     app.py already drives, redesigned for a reviewer to scan at a glance:
     quality/validity/crawl-status badges up top, rejection/drift called
     out as alerts instead of buried table cells, datapoints grouped into
     Identity / Descriptive / Signals cards each showing its value next to
     a colored source badge, conflict_check surfaced as its own panel, and
     a running session history table so multiple pages can be compared in
     one sitting.
  2. "Unified Row Preview" - a live demo of the new silver/company/ and
     silver/people/ connectors built in this same restructure. Clearly
     labeled preview: nothing here is wired into a production pipeline
     pending admin sign-off on the restructure - it exists so a reviewer
     can see the new architecture's *output shape* today, using real
     connector code against manually entered stand-in Apify/Prospeo
     fields (since silver/apify/ and silver/prospeo/ have no live scraper
     wired in yet).
"""
import json

import pandas as pd
import streamlit as st

from silver.company.connector import assemble_company_row
from silver.firecrawl import Firecrawl
from silver.people.connector import assemble_person_row
from silver.silver_orchestrator.contracts import DATAPOINT_CONTRACTS
from silver.silver_orchestrator.orchestrator import SilverOrchestrator

st.set_page_config(page_title="Silver Layer Audit", layout="wide")

_SOURCE_COLORS = {
    "context": "#1f77b4",
    "markdown": "#2ca02c",
    "markdown_fallback": "#ff7f0e",
    "hreflang": "#9467bd",
    "html": "#17becf",
    None: "#999999",
}
_DATAPOINT_GROUPS = {
    "Identity (join keys)": ["domain_normalize", "company_entity_resolve"],
    "Descriptive": ["company_description_extract", "legal_entity_extract", "business_model"],
    "Signals": [
        "tech_stack_normalize", "compliance_framework_extract", "experience_signal_extract",
        "service_region_extract", "pricing_locale_extract", "careers_page_parse",
        "social_links_extract", "site_locale_detect", "date_normalize",
    ],
}


@st.cache_resource
def get_orchestrator() -> SilverOrchestrator:
    return SilverOrchestrator(Firecrawl())


def _source_chip(source) -> str:
    color = _SOURCE_COLORS.get(source, "#999999")
    label = source or "empty"
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color};'
        f'border-radius:999px;padding:1px 8px;font-size:0.75em;font-weight:600;">{label}</span>'
    )


def _quality_color(score: float) -> str:
    if score >= 80:
        return "#2ca02c"
    if score >= 50:
        return "#ff7f0e"
    return "#d62728"


def _render_audit_header(row: dict):
    score = row.get("quality_score", 0.0)
    is_valid = bool(row.get("is_valid_row"))
    color = _quality_color(score)

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(
        f'<div style="font-size:2em;font-weight:700;color:{color};">{score:.0f}/100</div>'
        f'<div style="color:#666;">Quality score</div>',
        unsafe_allow_html=True,
    )
    col2.markdown(
        ("✅ **Valid row**" if is_valid else "🚫 **Rejected row**"),
    )
    col3.markdown(f"**Crawl status:** `{row.get('crawl_status', '-')}`")
    col4.markdown(f"**Content integrity:** `{row.get('content_integrity', '-')}`")

    if not is_valid:
        st.error(f"Rejected - reasons: {row.get('rejection_reasons') or [row.get('crawl_issue')]}")
    if row.get("drift_warnings"):
        st.warning(f"Drift warnings: {row['drift_warnings']}")


def _render_conflicts(row: dict):
    locale_conflict = row.get("locale_conflict")
    name_conflict = row.get("company_name_conflict")
    if not locale_conflict and not name_conflict:
        return
    with st.expander("⚠️ conflict_check flagged a disagreement", expanded=True):
        if locale_conflict:
            st.write(f"**Locale conflict:** {row.get('locale_conflict_detail')}")
        if name_conflict:
            st.write(f"**Company name conflict:** {row.get('company_name_conflict_detail')}")


def _render_datapoints(row: dict, function_report: dict):
    for group_title, names in _DATAPOINT_GROUPS.items():
        with st.expander(group_title, expanded=(group_title == "Identity (join keys)")):
            for name in names:
                if name not in DATAPOINT_CONTRACTS:
                    continue
                value = row.get(name)
                source = (function_report.get(name) or {}).get("source")
                left, right = st.columns([4, 1])
                with left:
                    st.markdown(f"**{name}**")
                    if value in (None, [], {}):
                        st.caption("empty")
                    elif isinstance(value, (dict, list)):
                        st.json(value)
                    else:
                        st.write(value)
                with right:
                    st.markdown(_source_chip(source), unsafe_allow_html=True)


def _flatten_row(row: dict) -> dict:
    return {
        key: value if isinstance(value, (str, int, float, bool, type(None))) else json.dumps(value, default=str)
        for key, value in row.items()
    }


def _run_firecrawl_audit_tab():
    orchestrator = get_orchestrator()

    st.caption("Paste or upload cleaned markdown from a scraped page - same pipeline as app.py, redesigned for scanning at a glance.")

    uploaded_file = st.file_uploader("Upload a markdown file", type=["md", "markdown", "txt"], key="v2_upload")
    pasted_markdown = st.text_area(
        "Or paste cleaned markdown", height=250, placeholder="Paste Firecrawl markdown here...", key="v2_paste"
    )
    markdown_input = uploaded_file.read().decode("utf-8") if uploaded_file is not None else pasted_markdown

    with st.expander("Optional context overrides"):
        col1, col2 = st.columns(2)
        with col1:
            source_url = st.text_input("source_url", key="v2_source_url")
            company_name = st.text_input("company_name", key="v2_company_name")
            company_description = st.text_input("company_description", key="v2_company_description")
        with col2:
            parent_guess = st.text_input("parent_guess", key="v2_parent_guess")
            entity_id = st.text_input("entity_id", key="v2_entity_id")
            raw_date = st.text_input("raw_date", key="v2_raw_date")

    run_clicked = st.button("Run audit", type="primary", disabled=not markdown_input.strip(), key="v2_run")

    if run_clicked:
        overrides = {
            "source_url": source_url,
            "company_name": company_name,
            "company_description": company_description,
            "parent_guess": parent_guess,
            "entity_id": entity_id,
            "raw_date": raw_date,
        }
        overrides = {k: v for k, v in overrides.items() if v}

        row = orchestrator.process_page(markdown_input, overrides)
        function_report = {}
        if row.get("crawl_issue") == "none":
            # process_page() doesn't expose function_report (only
            # is_empty/violations derived from it) - re-run Firecrawl
            # directly, read-only, purely so this UI can show per-field
            # source badges. Cheap relative to a human staring at a table.
            function_report = orchestrator.firecrawl.run_all(markdown_input, **overrides)["function_report"]

        st.session_state["v2_last_result"] = row
        st.session_state["v2_last_function_report"] = function_report
        history = st.session_state.setdefault("v2_history", [])
        history.append({
            "quality_score": row.get("quality_score"),
            "is_valid_row": row.get("is_valid_row"),
            "crawl_status": row.get("crawl_status"),
            "domain_normalize": row.get("domain_normalize"),
        })

    if "v2_last_result" in st.session_state:
        row = st.session_state["v2_last_result"]
        function_report = st.session_state.get("v2_last_function_report", {})

        st.divider()
        _render_audit_header(row)
        _render_conflicts(row)
        st.subheader("Datapoints")
        _render_datapoints(row, function_report)

        st.download_button(
            "Download as CSV",
            pd.DataFrame([_flatten_row(row)]).to_csv(index=False).encode("utf-8"),
            file_name="firecrawl_result.csv",
            mime="text/csv",
            key="v2_download",
        )
        with st.expander("Raw JSON (excludes raw_markdown_input)"):
            st.json({k: v for k, v in row.items() if k != "raw_markdown_input"})
        with st.expander("Raw markdown input"):
            st.text(row.get("raw_markdown_input", ""))

    history = st.session_state.get("v2_history")
    if history:
        st.divider()
        st.subheader("Session history")
        st.dataframe(pd.DataFrame(history), use_container_width=True)


def _run_unified_preview_tab():
    st.warning(
        "Preview only - silver/company/ and silver/people/ are additive scaffolding from the "
        "2026-09-08 restructure, not wired into any production pipeline yet. This tab runs the "
        "real connector code against manually entered stand-in Apify/Prospeo fields, since "
        "silver/apify/ and silver/prospeo/ have no live scraper wired in yet."
    )

    company_tab, people_tab = st.tabs(["Company row", "Person row"])

    with company_tab:
        st.caption("Firecrawl half comes from the markdown below (real, live). Apify half is manually entered (no live Apify source yet).")
        markdown_input = st.text_area(
            "Cleaned markdown (drives domain/description/company_id via Firecrawl)",
            height=150, key="v2_company_markdown",
        )
        source_url = st.text_input("source_url", key="v2_company_source_url")
        col1, col2 = st.columns(2)
        with col1:
            apify_name = st.text_input("apify: name", key="v2_apify_name")
            apify_industry = st.text_input("apify: industry", key="v2_apify_industry")
            apify_headcount = st.number_input("apify: headcount", min_value=0, value=0, step=1, key="v2_apify_headcount")
        with col2:
            apify_location = st.text_input("apify: location", key="v2_apify_location")
            apify_linkedin = st.text_input("apify: linkedin_url", key="v2_apify_linkedin")
            source_link = st.text_input("source_link (batch/ingestion tag)", key="v2_company_source_link")

        if st.button("Assemble company row", key="v2_assemble_company", disabled=not markdown_input.strip()):
            firecrawl_row = Firecrawl().run_all(markdown_input, source_url=source_url)["row"]
            apify_company = {
                "name": apify_name or None,
                "industry": apify_industry or None,
                "headcount": apify_headcount or None,
                "location": apify_location or None,
                "linkedin_url": apify_linkedin or None,
            }
            result = assemble_company_row(apify_company, firecrawl_row, source_link=source_link or None)
            st.json(result)

    with people_tab:
        st.caption("Both halves are manually entered - no live Apify or Prospeo source wired in yet.")
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("apify: full_name", key="v2_people_full_name")
            job_title = st.text_input("apify: job_title", key="v2_people_job_title")
            seniority = st.text_input("apify: seniority", key="v2_people_seniority")
            employed_company = st.text_input("apify: employed_company", key="v2_people_employed_company")
        with col2:
            country = st.text_input("apify: country", key="v2_people_country")
            linkedin_url = st.text_input("apify: linkedin_url", key="v2_people_linkedin_url")
            linkedin_about = st.text_area("apify: linkedin_about", height=80, key="v2_people_about")
            email = st.text_input("prospeo: email", key="v2_people_email")
        people_source_link = st.text_input("source_link (batch/ingestion tag)", key="v2_people_source_link")

        if st.button("Assemble person row", key="v2_assemble_person"):
            apify_person = {
                "full_name": full_name or None,
                "job_title": job_title or None,
                "seniority": seniority or None,
                "employed_company": employed_company or None,
                "country": country or None,
                "linkedin_url": linkedin_url or None,
                "linkedin_about": linkedin_about or None,
            }
            prospeo_person = {"email": email or None}
            result = assemble_person_row(apify_person, prospeo_person, source_link=people_source_link or None)
            st.json(result)


st.title("Silver Layer Audit")

audit_tab, preview_tab = st.tabs(["🔍 Firecrawl Audit", "🧩 Unified Row Preview"])
with audit_tab:
    _run_firecrawl_audit_tab()
with preview_tab:
    _run_unified_preview_tab()
