"""Venue-local time handling. The venue's wall-clock time and IANA time zone are stored as entered; the UTC
instant is derived on demand, so a zone-rule change (e.g. DST) never silently corrupts stored data."""
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return False


def to_utc(day: date, local_time: time | None, tz_name: str | None) -> datetime | None:
    """UTC instant of the start, or None when the time or zone is unknown (never guessed)."""
    if local_time is None or not tz_name or not valid_timezone(tz_name):
        return None
    return datetime.combine(day, local_time.replace(tzinfo=None), tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)
