"""Shared base for every datapoint extractor.

Subclassing DataPointExtractor auto-registers the class in REGISTRY the
moment its module is imported - the orchestrator in firecrawl.py builds its
extractor list from REGISTRY rather than holding a hardcoded list. Adding
datapoint #N is: create one file under datapoints/, subclass
DataPointExtractor there, add one import line in __init__.py (positioned
wherever its dependencies require in the execution order). firecrawl.py
itself never needs to change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

REGISTRY: List[Type["DataPointExtractor"]] = []


@dataclass
class DataPointResult:
    """Wrap a return value when an extractor needs to report more than its
    plain value:

    - `source`: where the value came from (e.g. "structured_data" vs
      "context_override" vs "heuristic") - lets a reviewer see when a
      lower-confidence guess was used instead of higher-confidence
      structured data.
    - `extra_columns`: additional flat columns to merge into the result
      row alongside this extractor's own column - used by conflict_check.py
      to emit `*_conflict` flags without inventing a second extraction
      pass over the page.
    """

    value: Any
    source: Optional[str] = None
    extra_columns: Dict[str, Any] = field(default_factory=dict)


class DataPointExtractor(ABC):
    """Base class every datapoints/*.py module implements."""

    name: str = "unnamed"

    def __init__(self):
        # Subclasses may set this inside extract() to record where their
        # value came from (e.g. "context", "markdown", "markdown_fallback",
        # "hreflang", "html") - readable without parsing the return value,
        # and read by Firecrawl.run_all() to build its function_report.
        self._last_source: Optional[str] = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        REGISTRY.append(cls)

    @abstractmethod
    def extract(self, markdown: str, context: dict) -> Any:
        """Return this datapoint's value (or a DataPointResult) given the
        cleaned markdown and the accumulated context (caller overrides +
        prior extractors' results, each keyed by its own .name)."""
