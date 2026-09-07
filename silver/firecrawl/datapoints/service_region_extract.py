"""function_service_region_extract(markdown) -> list of place strings,
unnormalized, exactly as found (e.g. ["Berlin, Germany", "Remote (EU)",
"Texas", "Barbados"]).

Distinct from site_locale_detect: that is language, this is geography.
Uses `geotext` for city/country detection when the optional dependency is
installed, and always also runs a conservative regex pass (in <City>,
<Country>; <City>, <StateAbbr>; Remote (<region>); and the 50 US state
names/abbreviations) so the function degrades gracefully without it.
"""
import re

from ..base import DataPointExtractor

try:
    from geotext import GeoText
except ImportError:  # pragma: no cover - optional dependency
    GeoText = None

_US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}
_US_STATE_ABBR = set(_US_STATES.values())

_IN_CITY_COUNTRY_RE = re.compile(
    r"\bin\s+([A-Z][\w.\-]*(?:\s+[A-Z][\w.\-]*)*,\s*[A-Z][\w.\-]*(?:\s+[A-Z][\w.\-]*)*)\b"
)
_CITY_STATE_ABBR_RE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*),\s*([A-Z]{2})\b")
_REMOTE_REGION_RE = re.compile(r"\bRemote\s*\([^)]+\)")
_STATE_NAME_RE = re.compile(r"\b(" + "|".join(re.escape(name) for name in _US_STATES) + r")\b")
_STATE_ABBR_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted(_US_STATE_ABBR)) + r")(?![A-Za-z])")


class ServiceRegionExtract(DataPointExtractor):
    name = "service_region_extract"

    def extract(self, markdown: str, context: dict):
        found = []

        if GeoText is not None:
            geo = GeoText(markdown)
            found.extend(geo.cities)
            found.extend(geo.countries)

        found.extend(m.group(1) for m in _IN_CITY_COUNTRY_RE.finditer(markdown))

        for m in _CITY_STATE_ABBR_RE.finditer(markdown):
            if m.group(2) in _US_STATE_ABBR:
                found.append(m.group(0))

        found.extend(m.group(0) for m in _REMOTE_REGION_RE.finditer(markdown))
        found.extend(m.group(1) for m in _STATE_NAME_RE.finditer(markdown))
        found.extend(m.group(1) for m in _STATE_ABBR_RE.finditer(markdown))

        seen = set()
        deduped = []
        for place in found:
            key = place.strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(key)
        self._last_source = "markdown" if deduped else None
        return deduped
