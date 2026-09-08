"""Tests for SilverOrchestrator, driven by the same fixtures as
firecrawl/tests/ (sample_input.md, sample_context.json) plus small inline
snippets for the rejection paths. Each test gets its own tmp_path-scoped
DeadLetterQueue/DriftTracker so dead_letter.jsonl / quality_history.jsonl
assertions are deterministic and tests never share state.
"""
import json
from pathlib import Path

from silver.firecrawl import Firecrawl
from silver.silver_orchestrator import schema_gate
from silver.silver_orchestrator.contracts import APIFY_COMPANY_CONTRACTS, DATAPOINT_CONTRACTS
from silver.silver_orchestrator.dead_letter import DeadLetterQueue
from silver.silver_orchestrator.drift import DriftTracker
from silver.silver_orchestrator.orchestrator import (
    SilverOrchestrator,
    build_function_report,
    evaluate_record,
)

FIRECRAWL_FIXTURES_DIR = Path(__file__).parent.parent.parent / "firecrawl" / "tests"
SAMPLE_MD = (FIRECRAWL_FIXTURES_DIR / "sample_input.md").read_text(encoding="utf-8")
SAMPLE_CONTEXT = json.loads((FIRECRAWL_FIXTURES_DIR / "sample_context.json").read_text(encoding="utf-8"))

LOTTERY_SNIPPET = (
    "## Tonight's Draw Results\n\n"
    "The winning numbers for tonight's lottery jackpot were 4, 8, 15, 16, 23, 42.\n"
)

MISSING_DOMAIN_SNIPPET = (
    "Acme Corp is a growing analytics company. Acme Corp works with mid-market "
    "retailers to unify their reporting. Acme Corp has no links on this page at all."
)

UNDER_CONSTRUCTION_SNIPPET = (
    "# Acme Corp\n\nOur new site is coming soon. Please check back later "
    "for updates on our services.\n"
)

DIRECTORY_SNIPPET = (
    "## Top 10 IT Support Companies in Denver\n\n"
    "**Acme IT** - Denver, CO - rated 4.8/5\n\n"
    "Acme IT offers managed services to local businesses.\n\n"
    "**Bolt Networks** - Denver, CO - rated 4.6/5\n\n"
    "Bolt Networks provides cloud migration support.\n\n"
    "**Circuit Systems** - Denver, CO - rated 4.3/5\n\n"
    "Circuit Systems handles network security for SMBs.\n"
)

PLACEHOLDER_TEMPLATE_SNIPPET = (
    "# Acme Corp\n\n"
    "Acme Corp is a growing analytics company. Acme Corp works with "
    "mid-market retailers to unify their reporting. Visit https://acme-example.com "
    "for more information about our platform and services today.\n\n"
    "## About\n\n"
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent sapien "
    "massa, convallis a pellentesque nec, egestas non nisi.\n"
)


def _make_orchestrator(tmp_path):
    dead_letter = DeadLetterQueue(path=str(tmp_path / "dead_letter.jsonl"))
    drift = DriftTracker(path=str(tmp_path / "quality_history.jsonl"))
    return SilverOrchestrator(Firecrawl(), dead_letter=dead_letter, drift=drift)


def test_process_page_accepts_sample_input(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    row = orchestrator.process_page(SAMPLE_MD, SAMPLE_CONTEXT)
    assert row["is_valid_row"] is True
    assert row["quality_score"] > 0
    assert row["rejection_reasons"] == []
    assert row["crawl_issue"] == "none"
    assert row["crawl_status"] in ("ok", "partial")
    assert row["content_integrity"] == "genuine"
    assert row["schema_version"] == "1.0"


def test_process_page_rejects_lottery_content(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    row = orchestrator.process_page(LOTTERY_SNIPPET)

    assert row is not None
    assert row["is_valid_row"] is False
    assert row["quality_score"] == 0.0
    # Caught by the new, earlier, more specific crawl_issue ladder now -
    # not by is_company_profile's own "not_a_company_profile" label, which
    # this exact input used to trigger before triage.py existed.
    assert row["rejection_reasons"] == ["non_company_page"]
    assert row["crawl_issue"] == "non_company_page"
    assert row["crawl_status"] == "unusable"
    assert row["content_integrity"] == "unknown"
    assert row["schema_version"] == "1.0"

    dead_letter_path = tmp_path / "dead_letter.jsonl"
    lines = dead_letter_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["reasons"] == ["non_company_page"]
    assert record["raw_input"] == LOTTERY_SNIPPET
    assert record["source"] == "firecrawl"


def test_process_page_rejects_snippet_missing_domain(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    row = orchestrator.process_page(MISSING_DOMAIN_SNIPPET)

    assert row is not None
    assert row["is_valid_row"] is False
    assert any("domain_normalize" in reason for reason in row["rejection_reasons"])
    # Short but genuine descriptive prose - triage should wave it through
    # as "partial", not reject it as boilerplate_only, so it still reaches
    # schema_gate and fails for the reason this test actually exercises.
    assert row["crawl_issue"] == "none"
    assert row["crawl_status"] == "partial"

    dead_letter_path = tmp_path / "dead_letter.jsonl"
    lines = dead_letter_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert any("domain_normalize" in reason for reason in record["reasons"])


def test_process_page_rejects_under_construction(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    row = orchestrator.process_page(UNDER_CONSTRUCTION_SNIPPET)

    assert row["is_valid_row"] is False
    assert row["rejection_reasons"] == ["under_construction"]
    assert row["crawl_issue"] == "under_construction"
    assert row["crawl_status"] == "unusable"
    assert row["content_integrity"] == "unknown"
    # Firecrawl never ran - stub row, every contracted field is None.
    assert row["domain_normalize"] is None
    assert row["company_entity_resolve"] is None


def test_process_page_rejects_directory_page(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    row = orchestrator.process_page(DIRECTORY_SNIPPET)

    assert row["is_valid_row"] is False
    assert row["rejection_reasons"] == ["directory_or_aggregator"]
    assert row["crawl_issue"] == "directory_or_aggregator"
    assert row["crawl_status"] == "unusable"


def test_process_page_flags_placeholder_content_independent_of_validity(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    row = orchestrator.process_page(
        PLACEHOLDER_TEMPLATE_SNIPPET, {"source_url": "https://acme-example.com"}
    )

    # The point of content_integrity: a row can pass every schema_gate
    # hard requirement and still be flagged as demo/theme content -
    # is_valid_row and content_integrity are independent signals.
    assert row["is_valid_row"] is True
    assert row["content_integrity"] == "placeholder_or_template"
    assert row["crawl_issue"] == "none"


def test_process_batch_keeps_every_row_with_valid_rows_first(tmp_path):
    orchestrator = _make_orchestrator(tmp_path)
    df = orchestrator.process_batch([
        {"markdown": SAMPLE_MD, "context": SAMPLE_CONTEXT},
        {"markdown": LOTTERY_SNIPPET, "context": None},
    ])

    assert len(df) == 2
    assert bool(df.iloc[0]["is_valid_row"]) is True
    assert bool(df.iloc[1]["is_valid_row"]) is False


def test_is_drifting_false_on_fresh_history(tmp_path):
    drift = DriftTracker(path=str(tmp_path / "quality_history.jsonl"))
    assert drift.is_drifting("domain_normalize") is False


def test_schema_gate_flags_placeholder_strings():
    row = {name: None for name in DATAPOINT_CONTRACTS}
    row["domain_normalize"] = "acme.com"
    row["company_entity_resolve"] = {"company_id": "acme"}
    row["site_locale_detect"] = "Unknown"

    violations = schema_gate.evaluate_row(row)

    assert any("site_locale_detect" in v and "placeholder" in v for v in violations)


def test_build_function_report_flags_blank_fields_as_empty():
    row = {"name": "Acme Corp", "industry": None, "headcount": 340, "location": None, "linkedin_url": ""}

    report = build_function_report(row, source="apify")

    assert report["name"] == {"ran": True, "is_empty": False, "source": "apify"}
    assert report["industry"] == {"ran": True, "is_empty": True, "source": "apify"}
    assert report["location"]["is_empty"] is True
    assert report["linkedin_url"]["is_empty"] is True


def test_evaluate_record_scores_and_gates_an_apify_company_row(tmp_path):
    row = {
        "name": "Acme Corp",
        "industry": "Logistics Software",
        "headcount": 340,
        "location": "Austin, TX",
        "linkedin_url": "https://linkedin.com/company/acme-corp",
    }
    function_report = build_function_report(row, source="apify")
    dead_letter = DeadLetterQueue(path=str(tmp_path / "dead_letter.jsonl"))
    drift = DriftTracker(path=str(tmp_path / "quality_history.jsonl"))

    result = evaluate_record(
        row, function_report, APIFY_COMPANY_CONTRACTS, "apify_company", dead_letter=dead_letter, drift=drift
    )

    assert result["is_valid_row"] is True
    assert result["quality_score"] == 100.0
    assert result["rejection_reasons"] == []
    assert result["drift_warnings"] == []
    assert result["schema_version"] == "1.0"
    assert result["name"] == "Acme Corp"
    assert not (tmp_path / "dead_letter.jsonl").exists()


def test_evaluate_record_dead_letters_placeholder_strings(tmp_path):
    row = {"name": "Acme Corp", "industry": "Unknown", "headcount": None, "location": None, "linkedin_url": None}
    function_report = build_function_report(row, source="apify")
    dead_letter = DeadLetterQueue(path=str(tmp_path / "dead_letter.jsonl"))
    drift = DriftTracker(path=str(tmp_path / "quality_history.jsonl"))

    result = evaluate_record(
        row, function_report, APIFY_COMPANY_CONTRACTS, "apify_company", dead_letter=dead_letter, drift=drift
    )

    assert result["is_valid_row"] is False
    assert any("industry" in reason and "placeholder" in reason for reason in result["rejection_reasons"])

    record = json.loads((tmp_path / "dead_letter.jsonl").read_text(encoding="utf-8").strip())
    assert record["source"] == "apify_company"
    assert json.loads(record["raw_input"])["name"] == "Acme Corp"


def test_drift_namespace_prevents_cross_source_collision(tmp_path):
    """Same function name ("location"), two sources writing to the same
    shared JSONL file: without namespacing, this is exactly the collision
    scenario found in review - an Apify pipeline and a Firecrawl pipeline
    sharing a field name would interleave in each other's rolling-window
    history. record_run/is_drifting's namespace param keys them apart."""
    drift = DriftTracker(path=str(tmp_path / "quality_history.jsonl"))

    drift.record_run("location", False)  # bare/firecrawl namespace
    drift.record_run("location", True, namespace="apify_company")  # separate namespace, same function name

    bare_records = drift._read_records("location")
    namespaced_records = drift._read_records("location", namespace="apify_company")

    assert len(bare_records) == 1 and bare_records[0]["is_empty"] is False
    assert len(namespaced_records) == 1 and namespaced_records[0]["is_empty"] is True
    assert bare_records[0]["function_name"] == "location"
    assert namespaced_records[0]["function_name"] == "apify_company:location"
