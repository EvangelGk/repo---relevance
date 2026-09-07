"""function_compliance_framework_extract(markdown) -> list of recognized
framework codes found, e.g. ["ISO27001", "SOC2", "HIPAA"].

Case-insensitive, word-boundary alias matching against a canonical code
table. An empty list is the correct, expected answer for most non-
compliance pages - it is not a sign the function failed.
"""
import re

from ..base import DataPointExtractor

_ALIASES = {
    "ISO27001": ["ISO 27001", "ISO/IEC 27001", "ISO27001"],
    "SOC2": ["SOC 2", "SOC2"],
    "NIST": ["NIST"],
    "HIPAA": ["HIPAA"],
    "PCI-DSS": ["PCI DSS", "PCI-DSS"],
    "GDPR": ["GDPR"],
    "CMMC": ["CMMC"],
    "DFARS": ["DFARS"],
    "FEDRAMP": ["FedRAMP", "FED RAMP"],
    "NIS2": ["NIS2", "NIS 2"],
    "CYBERSECURE_CANADA": ["CyberSecure Canada"],
}


def _build_patterns():
    compiled = {}
    for code, aliases in _ALIASES.items():
        alternatives = [re.escape(alias).replace(r"\ ", r"\s+") for alias in aliases]
        compiled[code] = re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)
    return compiled


_PATTERNS = _build_patterns()


class ComplianceFrameworkExtract(DataPointExtractor):
    name = "compliance_framework_extract"

    def extract(self, markdown: str, context: dict):
        found = [code for code, pattern in _PATTERNS.items() if pattern.search(markdown)]
        self._last_source = "markdown" if found else None
        return found
