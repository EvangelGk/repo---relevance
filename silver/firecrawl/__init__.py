from .base import DataPointExtractor, DataPointResult, REGISTRY

# Triggers every datapoints/*.py module's registration into REGISTRY via
# DataPointExtractor.__init_subclass__. See datapoints/__init__.py for the
# import order, which doubles as execution order (later extractors read
# earlier ones' output out of `context`) - that's also where a new
# datapoint's import line goes; nothing here or in firecrawl.py changes.
from . import datapoints  # noqa: F401

from .firecrawl import Firecrawl

__all__ = ["Firecrawl", "DataPointExtractor", "DataPointResult", "REGISTRY"]
