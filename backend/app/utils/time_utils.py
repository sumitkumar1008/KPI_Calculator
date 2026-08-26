"""
Time & Datetime Parsing Utilities
=================================
Provides robust datetime parsing and timedelta duration formatting for KPI calculations.

Features:
---------
1. parse_datetime: Parses string datetimes, pandas Timestamps, Python datetimes,
   and Excel serial float numbers into standard Python datetime objects.
2. safe_timediff: Computes difference between two datetime objects (end_dt - start_dt).
3. format_timedelta: Converts a timedelta into formatted string:
   - For < 24 hours: "HH:MM:SS" (zero-padded 2-digit hours, minutes, seconds).
   - For >= 24 hours: "Xd HH:MM:SS" (e.g. "1d 04:00:00").
"""

import datetime as _dt
import re
from datetime import datetime, timedelta
from typing import Any

try:
    import pandas as _pd

    _HAS_PANDAS = True
except Exception:
    _HAS_PANDAS = False

# Base Excel Epoch date (1899-12-30) for converting floating point serial date values
_EXCEL_EPOCH = datetime(1899, 12, 30)

# Comprehensive tuple of supported datetime string formats (including 12-hour AM/PM and 24-hour formats)
_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %I:%M:%S %p",
    "%Y/%m/%d %I:%M:%S %p",
    "%d-%m-%Y %I:%M:%S %p",
    "%d/%m/%Y %I:%M:%S %p",
    "%m/%d/%Y %I:%M:%S %p",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d %I:%M %p",
    "%Y/%m/%d %I:%M %p",
    "%d-%m-%Y %I:%M %p",
    "%d/%m/%Y %I:%M %p",
    "%m/%d/%Y %I:%M %p",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def parse_datetime(value: Any) -> datetime | None:
    """
    Parses a raw cell input into a naive Python datetime object.
    
    Supports:
    - None / empty string -> returns None
    - float / int (Excel serial numbers, e.g. 45142.675) -> converts relative to 1899-12-30
    - datetime / pandas Timestamp -> converts to naive datetime
    - string -> parses via strptime format whitelist, pandas to_datetime, or ISO format
    """
    if value is None:
        return None
    if isinstance(value, float):
        try:
            return _EXCEL_EPOCH + timedelta(days=float(value))
        except Exception:
            return None
    if isinstance(value, int):
        try:
            return _EXCEL_EPOCH + timedelta(days=float(value))
        except Exception:
            return None
    if isinstance(value, datetime):
        return value
    if _HAS_PANDAS:
        if isinstance(value, _pd.Timestamp):
            try:
                ts = value.to_pydatetime()
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                return ts
            except Exception:
                return None
        if value is _pd.NaT:
            return None
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return None
        # Try explicit format whitelist
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        # Fallback to pandas flexible string parser if available
        if _HAS_PANDAS:
            try:
                dt_pd = _pd.to_datetime(s)
                if not _pd.isna(dt_pd):
                    ts = dt_pd.to_pydatetime()
                    if ts.tzinfo is not None:
                        ts = ts.replace(tzinfo=None)
                    return ts
            except Exception:
                pass
        try:
            return datetime.fromisoformat(s)
        except Exception:
            pass
        if re.fullmatch(r"\d+(\.\d+)?", s):
            try:
                return _EXCEL_EPOCH + timedelta(days=float(s))
            except Exception:
                return None
        return None
    try:
        return datetime(
            value.year,
            value.month,
            value.day,
            getattr(value, "hour", 0),
            getattr(value, "minute", 0),
            getattr(value, "second", 0),
            getattr(value, "microsecond", 0),
        )
    except Exception:
        return None


def safe_timediff(end_dt: datetime | None, start_dt: datetime | None) -> timedelta | None:
    """
    Safely subtracts two datetime objects: end_dt - start_dt.
    Returns None if either timestamp is missing or invalid.
    """
    if end_dt is None or start_dt is None:
        return None
    if not isinstance(end_dt, datetime) or not isinstance(start_dt, datetime):
        return None
    return end_dt - start_dt


def get_timedelta_seconds(td: timedelta | None) -> float | int | None:
    """
    Returns total non-negative seconds for a timedelta object.
    Returns integer if whole seconds, or float if fractional seconds exist.
    Returns None if td is None, not a timedelta, or negative.
    """
    if td is None or not isinstance(td, timedelta):
        return None
    sec_float = td.total_seconds()
    if sec_float < 0:
        return None
    if sec_float.is_integer():
        return int(sec_float)
    return round(sec_float, 2)


def format_timedelta(td: timedelta | None) -> str | None:
    """
    Formats a non-negative timedelta object into standardized string output per Q1 policy:
    - For < 24 hours: "HH:MM:SS" (e.g. "06:00:00")
    - For >= 24 hours: "Xd HH:MM:SS" (e.g. "1d 04:00:00")
    
    Raises ValueError if td is negative. Caller handles Q2 policy (null KPI + row warning).
    """
    if td is None:
        return None
    if not isinstance(td, timedelta):
        return None
    sec_float = td.total_seconds()
    if sec_float < 0:
        raise ValueError("format_timedelta does not accept negative timedeltas; caller must handle per policy (Q2: null + warning)")
    
    total_seconds = round(sec_float)
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

