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
from silver.silver_orchestrator.contracts import DATAPOINT_CONTRACTS
from silver.silver_orchestrator.dead_letter import DeadLetterQueue
from silver.silver_orchestrator.drift import DriftTracker
from silver.silver_orchestrator.orchestrator import SilverOrchestrator

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
    assert record["raw_markdown_input"] == LOTTERY_SNIPPET


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
    row = orchestrator.process_page(PLACEHOLDER_TEMPLATE_SNIPPET)

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
