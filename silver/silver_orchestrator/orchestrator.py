"""SilverOrchestrator: the Silver-layer gate in front of Firecrawl.

Firecrawl itself is pure execution now - it runs every registered datapoint
function against whatever it's given and reports what happened, never deciding
pass/fail or skipping itself. This module owns that decision: whether a
page is worth running Firecrawl on at all (is_company_profile, moved here
from firecrawl.py, plus the richer triage.classify_crawl_issue ladder in
front of it), and whether the row Firecrawl produced is good enough to
trust (schema_gate + quality_score + drift).

process_page() always returns a row - never None. A rejected page still
produces a visibly-flagged row (is_valid_row=False, a quality_score, and
rejection_reasons) so it survives into the final CSV instead of only
existing in dead_letter.jsonl - the CSV is the primary place a human sees a
rejection; dead_letter.jsonl is a secondary trail for triage/replay
tooling.

Every row also carries crawl_issue/crawl_status (triage.classify_crawl_issue),
content_integrity (triage.classify_content_integrity), and schema_version -
added 2026-09-07, adapted from a B2B account-research crawl-extraction
prompt (Cowork Project schema-inspiration proposal). content_integrity is
forced to "unknown" whenever crawl_status is "unusable", mirroring that
source prompt's rule that a failed/rejected fetch carries no content
signal worth reporting.

Generalized 2026-09-08 to cover the rest of silver/, not just Firecrawl:
`build_function_report`/`evaluate_record` below are the module's other
half, used by silver/company/connector.py and silver/people/connector.py
to gate an Apify-extracted row through the same schema_gate/quality_score/
drift machinery process_page() uses - without the crawl_issue/
is_company_profile/content_integrity concepts, which are specific to "was
this a usable scraped webpage" and don't apply to an already-structured
record. See triage.py's module docstring for why that stage is skipped
rather than adapted.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from . import quality_score, schema_gate
from .contracts import DATAPOINT_CONTRACTS, DatapointContract
from .dead_letter import DeadLetterQueue
from .drift import DriftTracker
from .triage import classify_content_integrity, classify_crawl_issue

_LOTTERY_RE = re.compile(r"\b(draw results|winning numbers|lottery|jackpot)\b", re.IGNORECASE)
_LISTICLE_RE = re.compile(
    r"\b(top\s+\d+|best\s+\d+|\d+\s+(?:ways|tips|reasons|things|steps)|how\s+to|ultimate guide)\b",
    re.IGNORECASE,
)
_PARAGRAPH_SUBJECT_RE = re.compile(r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)\b")

# Bumped whenever a field is added/removed/retyped in the row this
# orchestrator emits - lets a downstream consumer (or a future migration
# check, per the monorepo's MIGRATION_POLICY.md pattern) tell which shape
# a given CSV/row was produced under.
_SCHEMA_VERSION = "1.0"


class SilverOrchestrator:
    def __init__(
        self,
        firecrawl: Optional[Any] = None,
        contracts: Dict[str, DatapointContract] = DATAPOINT_CONTRACTS,
        dead_letter: Optional[DeadLetterQueue] = None,
        drift: Optional[DriftTracker] = None,
    ):
        # firecrawl is optional (added 2026-09-08): process_page()/
        # process_batch() still need one, but evaluate_record() below
        # doesn't touch self.firecrawl at all, so a caller that only wants
        # the generic record-gating path (e.g. a future non-Firecrawl
        # pipeline) isn't forced to construct a Firecrawl instance just to
        # get one.
        self.firecrawl = firecrawl
        self.contracts = contracts
        self.dead_letter = dead_letter if dead_letter is not None else DeadLetterQueue()
        self.drift = drift if drift is not None else DriftTracker()

    def is_company_profile(self, markdown: str) -> bool:
        """Cheap heuristic relevance gate (not ML): reject pages that are
        clearly not a company profile before running Firecrawl's
        datapoint extractors against them - a lottery results page or a
        generic listicle has no business filling out a company row.

        Rejects when either is true:
        - strong non-company language fires (lottery/gambling results), or
        - the page reads as generic listicle/guide content AND no single
          capitalized multi-word phrase repeats as the paragraph-opening
          subject across 3+ paragraphs (the pattern an actual company
          profile has - "Acme Corp is...", "Acme Corp offers...", - and a
          generic "Top 10 ways to..." article does not).

        Note: the lottery branch is now also caught earlier, and more
        specifically, by triage.classify_crawl_issue's "non_company_page"
        - it stays here too because it's cheap and this method is still a
        public, independently-testable unit. The listicle-without-
        repeating-subject branch is this method's real remaining job.
        """
        markdown = markdown or ""
        if _LOTTERY_RE.search(markdown):
            return False

        if _LISTICLE_RE.search(markdown):
            subject_counts: Dict[str, int] = {}
            for paragraph in re.split(r"\n\s*\n", markdown):
                stripped = paragraph.strip().lstrip("#").strip()
                match = _PARAGRAPH_SUBJECT_RE.match(stripped)
                if match:
                    subject = match.group(1)
                    subject_counts[subject] = subject_counts.get(subject, 0) + 1
            if not any(count >= 3 for count in subject_counts.values()):
                return False

        return True

    def _stub_row(self, markdown: str, run_timestamp: str) -> dict:
        row: Dict[str, Any] = {name: None for name in self.contracts}
        row["raw_markdown_input"] = markdown
        row["run_timestamp"] = run_timestamp
        return row

    def _reject(
        self,
        markdown: str,
        run_timestamp: str,
        reasons: List[str],
        crawl_issue: str,
        crawl_status: str,
    ) -> dict:
        self.dead_letter.append(markdown, reasons, source="firecrawl")
        row = self._stub_row(markdown, run_timestamp)
        row["is_valid_row"] = False
        row["quality_score"] = 0.0
        row["rejection_reasons"] = reasons
        row["drift_warnings"] = []
        row["crawl_issue"] = crawl_issue
        row["crawl_status"] = crawl_status
        row["content_integrity"] = "unknown"
        row["schema_version"] = _SCHEMA_VERSION
        return row

    def process_page(self, markdown: str, context: Optional[dict] = None) -> dict:
        if self.firecrawl is None:
            raise ValueError(
                "SilverOrchestrator was constructed without a firecrawl instance - "
                "process_page()/process_batch() need one; evaluate_record() doesn't."
            )
        markdown = markdown or ""
        run_timestamp = datetime.now(timezone.utc).isoformat()

        crawl_issue, crawl_status = classify_crawl_issue(markdown)
        if crawl_issue != "none":
            # Firecrawl never runs here - the whole point of this gate is
            # skipping wasted computation on unusable content.
            return self._reject(markdown, run_timestamp, [crawl_issue], crawl_issue, crawl_status)

        if not self.is_company_profile(markdown):
            return self._reject(
                markdown, run_timestamp, ["not_a_company_profile"], "wrong_page_type", "unusable"
            )

        result = self.firecrawl.run_all(markdown, **(context or {}))
        row = result["row"]
        function_report = result["function_report"]

        violations = schema_gate.evaluate_row(row, contracts=self.contracts)
        score = quality_score.compute_quality_score(function_report, self.contracts)

        row["drift_warnings"] = []
        for name, entry in function_report.items():
            self.drift.record_run(name, entry["is_empty"])
            if self.drift.is_drifting(name):
                row["drift_warnings"].append(f"drift_warning:{name}")

        row["crawl_issue"] = crawl_issue  # "none" - reached this branch only when it is
        row["crawl_status"] = crawl_status  # "ok" or "partial"
        row["content_integrity"] = classify_content_integrity(markdown)
        row["schema_version"] = _SCHEMA_VERSION

        if violations:
            self.dead_letter.append(markdown, violations, source="firecrawl")
            row["is_valid_row"] = False
            row["quality_score"] = score
            row["rejection_reasons"] = violations
        else:
            row["is_valid_row"] = True
            row["quality_score"] = score
            row["rejection_reasons"] = []

        return row

    def process_batch(self, inputs: List[Dict[str, Any]]) -> pd.DataFrame:
        """Every input produces exactly one output row - nothing is
        dropped, this is the full audit trail for the batch. Valid rows
        sort before invalid ones; each group keeps its original relative
        order (stable sort)."""
        rows = [self.process_page(item.get("markdown", ""), item.get("context")) for item in inputs]
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        sort_key = (~df["is_valid_row"]).to_numpy()
        df = df.iloc[sort_key.argsort(kind="stable")].reset_index(drop=True)
        return df

    def run_and_save_csv(self, inputs: List[Dict[str, Any]], out_path: str) -> pd.DataFrame:
        df = self.process_batch(inputs)
        df.to_csv(out_path, index=False)
        return df


def _is_blank(value: Any) -> bool:
    """The same "nothing found" convention GROUNDING_LAW.md rule 4 and
    Firecrawl._collapse_if_blank already use - None/[]/{}/""."""
    return value is None or value in ([], {}, "")


def build_function_report(row: Dict[str, Any], source: str) -> Dict[str, dict]:
    """Turn a flat single-source extractor output - e.g.
    apify/company/universal/extract.py's extract_company_universal_fields()
    - into the {name: {ran, is_empty, source}} shape Firecrawl.run_all()
    already produces, so schema_gate/quality_score/drift can treat any
    flat-dict source uniformly via evaluate_record() below. Every entry
    gets ran=True: nothing in a flat single-pass extractor dict was ever
    "skipped" the way a firecrawl datapoint theoretically could be."""
    return {name: {"ran": True, "is_empty": _is_blank(value), "source": source} for name, value in row.items()}


def evaluate_record(
    row: Dict[str, Any],
    function_report: Dict[str, dict],
    contracts: Dict[str, DatapointContract],
    source_label: str,
    dead_letter: Optional[DeadLetterQueue] = None,
    drift: Optional[DriftTracker] = None,
) -> Dict[str, Any]:
    """The generic sibling of process_page()'s tail half (schema_gate +
    quality_score + drift), for record-shaped input that was never a
    crawled markdown page - an Apify company/person extraction, today.
    Deliberately skips crawl_issue/is_company_profile/content_integrity:
    those are all "was this a usable scraped webpage" concepts (see
    triage.py's module docstring) that don't apply to an already-
    structured record.

    `source_label` namespaces drift recording (see DriftTracker's
    `namespace` param) so an Apify function and a Firecrawl function that
    happen to share a name never corrupt each other's rolling-window
    baseline, and tags the dead-letter record when this row is rejected.

    Returns `row` plus is_valid_row/quality_score/rejection_reasons/
    drift_warnings/schema_version - the same result shape process_page()
    returns, minus the crawl-specific fields it doesn't have a value for.
    """
    dead_letter = dead_letter if dead_letter is not None else DeadLetterQueue()
    drift = drift if drift is not None else DriftTracker()

    violations = schema_gate.evaluate_row(row, contracts=contracts)
    score = quality_score.compute_quality_score(function_report, contracts)

    drift_warnings: List[str] = []
    for name, entry in function_report.items():
        drift.record_run(name, entry["is_empty"], namespace=source_label)
        if drift.is_drifting(name, namespace=source_label):
            drift_warnings.append(f"drift_warning:{name}")

    result = dict(row)
    result["is_valid_row"] = not violations
    result["quality_score"] = score
    result["rejection_reasons"] = violations
    result["drift_warnings"] = drift_warnings
    result["schema_version"] = _SCHEMA_VERSION

    if violations:
        dead_letter.append(row, violations, source=source_label)

    return result
