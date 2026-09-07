"""Local JSONL audit trail for rows the orchestrator rejected.

This is deliberately local to silver_orchestrator, not the shared Supabase
ledger - that belongs to the full Artemis orchestrator, a later layer. This
queue is a SECONDARY trail for triage/replay tooling: a rejected row still
gets a visible, flagged row in the primary CSV output (see
orchestrator.SilverOrchestrator.process_page) - this file is written
alongside that row, never instead of it.
"""
import json
import os
from datetime import datetime, timezone
from typing import List

# Anchored to this module's own location, not the caller's cwd - a bare
# "silver_orchestrator/data/..." default silently landed in the wrong place
# (a stray top-level silver_orchestrator/ directory) whenever the caller's
# cwd was the repo root rather than silver/, e.g. `streamlit run app.py` or
# `pytest` invoked from the repo root.
_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dead_letter.jsonl")


class DeadLetterQueue:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path

    def append(self, raw_markdown_input: str, reasons: List[str]) -> None:
        parent_dir = os.path.dirname(self.path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reasons": reasons,
            "raw_markdown_input": raw_markdown_input,
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
