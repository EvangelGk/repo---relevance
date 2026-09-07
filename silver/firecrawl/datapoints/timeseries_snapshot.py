"""function_timeseries_snapshot(field value, snapshot date, entity id) ->
versioned_series[]

In production this appends to a stored history keyed by entity_id; run
standalone against one page it returns the single new point the caller
should append to that series. Defaults to snapshotting
structured_data_extract's numberOfEmployees when no explicit
timeseries_value override is given, and reports which one it used as
`timeseries_snapshot_source` ("context_override" | "structured_data").
"""
from datetime import date

from ..base import DataPointExtractor, DataPointResult


class TimeseriesSnapshot(DataPointExtractor):
    name = "timeseries_snapshot"

    def extract(self, markdown: str, context: dict):
        field = context.get("timeseries_field") or "numberOfEmployees"
        value = context.get("timeseries_value")
        source = "context_override"
        if value is None and field == "numberOfEmployees":
            value = (context.get("structured_data_extract") or {}).get("numberOfEmployees")
            source = "structured_data"
        if value is None:
            self._last_source = None
            return None

        entity_id = context.get("entity_id") or (context.get("company_entity_resolve") or {}).get("company_id")
        snapshot_date = context.get("snapshot_date") or date.today().isoformat()
        point = [{
            "entity_id": entity_id,
            "field": field,
            "value": value,
            "snapshot_date": snapshot_date,
        }]
        self._last_source = "context"
        return DataPointResult(value=point, source=source)
