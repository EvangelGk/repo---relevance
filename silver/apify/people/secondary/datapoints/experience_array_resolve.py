"""function_experience_array_resolve(raw_experience: list[dict]) -> dict

Normalizes a person's raw LinkedIn work-history array (as returned by an
Apify LinkedIn profile scraper) into a consistent shape, and derives two
summary signals from it:

  - `total_years_experience`: sum of each entry's duration in years
    (entries are NOT deduplicated for overlap - two concurrent roles both
    count their full duration; documented limitation, not a bug)
  - `current_tenure_years`: duration of whichever entry has no end date
    (i.e. the current role), or the most recent entry's duration if none
    are open-ended

This is also this repo's people-side answer to the "years of
experience/tenure" concept that Firecrawl's `experience_signal_extract`
captures for companies from marketing prose - see
apify/people/secondary/README.md for why that doesn't get a separate
people-side clone.

Expected input shape, one dict per role:
    {"title": str, "company": str, "start_date": str, "end_date": str | None}
`start_date`/`end_date` accept "YYYY-MM", "YYYY", "Mon YYYY" (e.g. "Jan 2020"),
or None/"Present"/"Current" for `end_date` meaning ongoing.
"""
import re
from datetime import date
from typing import Any, Dict, List, Optional

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_ONGOING_TOKENS = {"present", "current", "now", ""}


def _parse_month_year(raw: Optional[str]):
    """Return (year, month) or None if unparseable. Missing month defaults to 1
    (start) or 12 (end) is handled by the caller, not here."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if not text or text in _ONGOING_TOKENS:
        return None
    match = re.match(r"^(\d{4})-(\d{1,2})$", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re.match(r"^(\d{4})$", text)
    if match:
        return int(match.group(1)), None
    match = re.match(r"^([a-z]{3,9})\.?\s+(\d{4})$", text)
    if match:
        month_name, year = match.group(1)[:3], match.group(2)
        if month_name in _MONTHS:
            return int(year), _MONTHS[month_name]
    return None


def _duration_years(start_raw: Optional[str], end_raw: Optional[str], today: date) -> Optional[float]:
    start = _parse_month_year(start_raw)
    if start is None:
        return None
    start_year, start_month = start[0], start[1] or 1

    end_text = "" if end_raw is None else str(end_raw).strip().lower()
    if end_text in _ONGOING_TOKENS:
        end_year, end_month = today.year, today.month
    else:
        end = _parse_month_year(end_raw)
        if end is None:
            return None
        end_year, end_month = end[0], end[1] or 12

    months = (end_year - start_year) * 12 + (end_month - start_month)
    return max(months, 0) / 12.0


def function_experience_array_resolve(
    raw_experience: Optional[List[Dict[str, Any]]],
    today: Optional[date] = None,
) -> Dict[str, Any]:
    today = today or date.today()
    entries = raw_experience or []

    normalized = []
    total_years = 0.0
    any_duration_known = False
    current_tenure_years = None
    latest_start_key = None
    latest_entry_duration = None

    for entry in entries:
        start_raw = entry.get("start_date")
        end_raw = entry.get("end_date")
        duration = _duration_years(start_raw, end_raw, today)
        is_current = end_raw is None or str(end_raw).strip().lower() in _ONGOING_TOKENS

        normalized.append({
            "title": entry.get("title"),
            "company": entry.get("company"),
            "start_date": start_raw,
            "end_date": end_raw,
            "duration_years": round(duration, 2) if duration is not None else None,
            "is_current": is_current,
        })

        if duration is not None:
            total_years += duration
            any_duration_known = True

        if is_current and duration is not None:
            current_tenure_years = round(duration, 2)

        start_key = _parse_month_year(start_raw)
        if start_key is not None and (latest_start_key is None or start_key > latest_start_key):
            latest_start_key = start_key
            latest_entry_duration = duration

    if current_tenure_years is None and latest_entry_duration is not None:
        current_tenure_years = round(latest_entry_duration, 2)

    return {
        "experiences": normalized,
        "total_years_experience": round(total_years, 2) if any_duration_known else None,
        "current_tenure_years": current_tenure_years,
    }
