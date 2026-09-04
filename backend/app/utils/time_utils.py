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

import math
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
        # Fast Path 1: Try native C-level ISO 8601 parser first (75x faster)
        try:
            return datetime.fromisoformat(s)
        except Exception:
            pass
        # Fast Path 2: Try explicit format whitelist
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
    Preserves exact fractional seconds without rounding.
    Returns None if td is None, not a timedelta, or negative.
    """
    if td is None or not isinstance(td, timedelta):
        return None
    sec_float = td.total_seconds()
    if sec_float < 0:
        return None
    if sec_float.is_integer():
        return int(sec_float)
    return sec_float


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


def parse_duration_to_seconds(val: Any) -> float | None:
    """
    Converts a duration / timing value into total seconds as an unrounded float.
    
    Supports:
    - Numeric values (int / float): e.g. 11945, 90.5, 0
    - datetime.timedelta objects: e.g. timedelta(hours=3, minutes=19, seconds=5)
    - datetime.time objects: e.g. time(3, 19, 5)
    - Standard duration strings in "HH:MM:SS" or "H:M:S": e.g. "03:19:05", "3:19:5"
    - Durations > 24 hours: e.g. "27:15:30", "100:00:00"
    - Fractional duration strings: e.g. "00:01:30.500", "03:19:05.25"
    - Day-based duration strings: e.g. "1d 04:00:00", "2 days 03:00:00"
    - "HH:MM" duration strings: e.g. "01:30" -> 5400s
    
    Excludes (returns None, never included in denominator):
    - None, empty strings, whitespace-only strings
    - Excel error cells: "#VALUE!", "#N/A", "#REF!", "#DIV/0!", "#NUM!", "#NAME?", "#NULL!"
    - Special string literals: "null", "none", "nan", "n/a", "nat", "-", "—"
    - Boolean values (True, False)
    - Negative durations or seconds (< 0)
    - Unparseable or malformed values
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, timedelta):
        s = val.total_seconds()
        return s if s >= 0 else None
    if isinstance(val, (datetime, _pd.Timestamp) if _HAS_PANDAS else (datetime,)):
        return None
    if hasattr(val, "hour") and hasattr(val, "minute") and hasattr(val, "second") and not hasattr(val, "year"):
        sec = val.hour * 3600.0 + val.minute * 60.0 + val.second + getattr(val, "microsecond", 0) / 1_000_000.0
        return float(sec)
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val) or val < 0:
            return None
        if isinstance(val, float) and 0 < val < 1.0:
            return float(val * 86400.0)
        return float(val)

    if not isinstance(val, str):
        val = str(val)

    s = val.strip()
    if not s:
        return None

    s_lower = s.lower()
    if s_lower in ("none", "null", "nan", "n/a", "nat", "-", "—", "undefined"):
        return None

    # Excel error formats (#VALUE!, #N/A, #REF!, #DIV/0!, #NUM!, #NAME?, #NULL!, etc.)
    if s.startswith("#"):
        return None

    days = 0.0
    if "d " in s_lower:
        d_str, s_lower = s_lower.split("d ", 1)
        try:
            days = float(d_str.strip())
        except ValueError:
            return None
    elif "days " in s_lower:
        d_str, s_lower = s_lower.split("days ", 1)
        try:
            days = float(d_str.strip())
        except ValueError:
            return None
    elif "day " in s_lower:
        d_str, s_lower = s_lower.split("day ", 1)
        try:
            days = float(d_str.strip())
        except ValueError:
            return None

    time_part = s_lower.strip()

    if ":" in time_part:
        parts = time_part.split(":")
        try:
            if len(parts) == 3:
                h = float(parts[0])
                m = float(parts[1])
                sec = float(parts[2])
                if h < 0 or m < 0 or sec < 0:
                    return None
                tot = days * 86400.0 + h * 3600.0 + m * 60.0 + sec
                return tot if tot >= 0 else None
            elif len(parts) == 2:
                h = float(parts[0])
                m = float(parts[1])
                if h < 0 or m < 0:
                    return None
                tot = days * 86400.0 + h * 3600.0 + m * 60.0
                return tot if tot >= 0 else None
        except ValueError:
            return None

    try:
        tot = float(time_part)
        if math.isnan(tot) or math.isinf(tot) or tot < 0:
            return None
        tot += days * 86400.0
        return tot if tot >= 0 else None
    except ValueError:
        return None


def format_duration_hhmmss(seconds: float | int | timedelta | None) -> str | None:
    """
    Converts duration seconds back to strict 'HH:MM:SS' format.
    
    Requirements:
    - Supports durations > 24 hours correctly; does NOT reset hours modulo 24 (e.g. 26:30:15, 105:00:00).
    - Hours, minutes, and seconds are zero-padded to at least 2 digits (e.g. 03:19:05).
    - Fractional seconds are rounded ONLY at this final formatting step.
    - Returns None for None, negative durations, NaNs, or errors.
    """
    if seconds is None:
        return None
    if isinstance(seconds, timedelta):
        sec_float = seconds.total_seconds()
    elif isinstance(seconds, bool):
        return None
    else:
        try:
            sec_float = float(seconds)
        except (ValueError, TypeError):
            return None

    if math.isnan(sec_float) or math.isinf(sec_float) or sec_float < 0:
        return None

    total_sec = round(sec_float)
    hours = total_sec // 3600
    rem = total_sec % 3600
    minutes = rem // 60
    secs = rem % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_duration_series(sec_series: Any) -> Any:
    """
    Vectorized conversion of a pandas Series of numeric seconds into 'HH:MM:SS' string format.
    Supports NaN/None handling cleanly at C-speed.
    """
    if not _HAS_PANDAS or not isinstance(sec_series, _pd.Series):
        return [format_duration_hhmmss(s) for s in sec_series]
    
    s_numeric = _pd.to_numeric(sec_series, errors="coerce")
    valid_mask = s_numeric.notna() & (s_numeric >= 0)
    
    res = _pd.Series(index=sec_series.index, dtype=object)
    if not valid_mask.any():
        return res
    
    sec_vals = s_numeric[valid_mask].round().astype("int64")
    hours = (sec_vals // 3600).astype(str).str.zfill(2)
    rem = sec_vals % 3600
    minutes = (rem // 60).astype(str).str.zfill(2)
    secs = (rem % 60).astype(str).str.zfill(2)
    
    formatted = hours + ":" + minutes + ":" + secs
    res.loc[valid_mask] = formatted
    return res


def compute_duration_average(values: list[Any]) -> tuple[str | None, int, float | None, float | None]:
    """
    Computes Excel-equivalent AVERAGE for a collection of duration / timing values.
    
    Formula:
        average_seconds = sum(valid_seconds) / count(valid_values)
        
    Rules:
    - Treat timing values as durations in HH:MM:SS format.
    - Convert each valid duration to total seconds before calculating the average.
    - Ignore blank cells, #VALUE!, invalid values, and other non-numeric/error values (not in denominator).
    - Do NOT round individual timing values before averaging.
    - Preserve fractional seconds during calculation and only round/format the final result.
    - Convert the final average seconds back to HH:MM:SS.
    - Support durations greater than 24 hours correctly (no reset after 24h).
    
    Returns:
        (formatted_hhmmss, count_valid, sum_seconds, avg_seconds)
    """
    valid_seconds: list[float] = []
    for v in values:
        sec = parse_duration_to_seconds(v)
        if sec is not None:
            valid_seconds.append(sec)

    count = len(valid_seconds)
    if count == 0:
        return None, 0, None, None

    total_sum = sum(valid_seconds)
    avg_sec = total_sum / count
    formatted = format_duration_hhmmss(avg_sec)
    return formatted, count, total_sum, avg_sec

