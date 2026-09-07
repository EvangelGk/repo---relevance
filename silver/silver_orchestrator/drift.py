"""Rolling-window drift detection for how often each datapoint function
comes back empty - adapted from the finance project's
`_resolve_dynamic_null_threshold` shape (historical mean + 2*std, capped)
but applied to a boolean empty-rate instead of a numeric series value.

Local JSONL history file, one line per (function, page) observation. Not a
hard gate: is_drifting() is a signal for a human to look at
(SilverOrchestrator surfaces it as row["drift_warnings"]), never a reason to
reject a row on its own.
"""
import json
import os
import statistics
from datetime import datetime, timezone
from typing import List

# Anchored to this module's own location, not the caller's cwd - see the
# matching comment in dead_letter.py for why a bare relative default is a
# footgun here (streamlit run app.py / pytest both run from the repo root).
_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "quality_history.jsonl")


class DriftTracker:
    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path

    def record_run(self, function_name: str, is_empty: bool) -> None:
        parent_dir = os.path.dirname(self.path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "function_name": function_name,
            "is_empty": bool(is_empty),
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def _read_records(self, function_name: str) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        records = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("function_name") == function_name:
                    records.append(record)
        return records

    def is_drifting(self, function_name: str, window: int = 20) -> bool:
        """True when the most recent recorded run for `function_name` is
        empty at a rate more than 2 std above the historical mean of the
        `window - 1` runs before it. Needs at least 5 historical (prior)
        records before it will ever flag drift - a thin history can't
        support a meaningful mean/std."""
        records = self._read_records(function_name)[-window:]
        if not records:
            return False

        *history, current = records
        if len(history) < 5:
            return False

        history_values = [1.0 if r["is_empty"] else 0.0 for r in history]
        mean = statistics.fmean(history_values)
        std = statistics.stdev(history_values) if len(history_values) > 1 else 0.0
        threshold = min(mean + 2 * std, 1.0)

        current_value = 1.0 if current["is_empty"] else 0.0
        return current_value > threshold
