"""Local JSONL audit trail for rows the orchestrator rejected.

This is deliberately local to silver_orchestrator, not the shared Supabase
ledger - that belongs to the full Artemis orchestrator, a later layer. This
queue is a SECONDARY trail for triage/replay tooling: a rejected row still
gets a visible, flagged row in the primary CSV output (see
orchestrator.SilverOrchestrator.process_page) - this file is written
alongside that row, never instead of it.

Generalized 2026-09-08 (behavior change): append() used to take only a
markdown string. It now takes `raw_input: Any` plus an optional `source`
label, since silver/company/connector.py and silver/people/connector.py
can now dead-letter a rejected Apify record (a dict), not just Firecrawl
markdown. The JSONL key holding that value was renamed
raw_markdown_input -> raw_input to match - it was never markdown-specific
in spirit, and keeping that name on a dict record would be misleading. A
non-string raw_input is JSON-serialized (default=str) before writing.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

# Anchored to this module's own location, not the caller's cwd - a bare
# "silver_orchestrator/data/..." default silently landed in the wrong place
# (a stray top-level silver_orchestrator/ directory) whenever the caller's
# cwd was the repo root rather than silver/, e.g. `streamlit run app.py` or
# `pytest` invoked from the repo root.
_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dead_letter.jsonl")


class DeadLetterQueue:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path

    def append(self, raw_input: Any, reasons: List[str], source: Optional[str] = None) -> None:
        parent_dir = os.path.dirname(self.path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reasons": reasons,
            "raw_input": raw_input if isinstance(raw_input, str) else json.dumps(raw_input, default=str),
            "source": source,
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
