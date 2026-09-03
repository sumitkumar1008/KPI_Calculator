import os
import sys
from datetime import datetime, timedelta
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.time_utils import format_timedelta, parse_datetime, safe_timediff


def test_parse_datetime_none():
    assert parse_datetime(None) is None
    assert parse_datetime("") is None
    assert parse_datetime("   ") is None


def test_parse_datetime_from_str_various_formats():
    assert parse_datetime("2026-08-21 08:00:00") == datetime(2026, 8, 21, 8, 0, 0)
    assert parse_datetime("2026/08/21 08:00:00") == datetime(2026, 8, 21, 8, 0, 0)
    assert parse_datetime("21-08-2026 08:00:00") == datetime(2026, 8, 21, 8, 0, 0)
    assert parse_datetime("2026-08-21") == datetime(2026, 8, 21, 0, 0, 0)


def test_parse_datetime_from_iso():
    assert parse_datetime("2026-08-21T08:00:00") == datetime(2026, 8, 21, 8, 0, 0)


def test_parse_datetime_from_python_datetime():
    dt = datetime(2026, 8, 21, 8, 0, 0)
    assert parse_datetime(dt) == dt


def test_parse_datetime_excel_serial():
    serial_1900_01_01 = 2.0
    dt = parse_datetime(serial_1900_01_01)
    assert dt is not None
    assert dt.year == 1900
    assert dt.month == 1
    assert dt.day == 1


def test_parse_datetime_invalid_str_returns_none():
    assert parse_datetime("not a date at all") is None


def test_safe_timediff_normal():
    a = datetime(2026, 8, 21, 12, 0, 0)
    b = datetime(2026, 8, 21, 14, 0, 0)
    assert safe_timediff(b, a) == timedelta(hours=2)


def test_safe_timediff_negative_is_permitted_returns_negative_td():
    a = datetime(2026, 8, 21, 14, 0, 0)
    b = datetime(2026, 8, 21, 12, 0, 0)
    diff = safe_timediff(b, a)
    assert diff is not None
    assert diff.total_seconds() < 0


def test_safe_timediff_none():
    a = datetime(2026, 8, 21, 8, 0, 0)
    assert safe_timediff(None, a) is None
    assert safe_timediff(a, None) is None
    assert safe_timediff(None, None) is None


def test_format_timedelta_zero():
    assert format_timedelta(timedelta(0)) == "00:00:00"


def test_format_timedelta_sub_24h():
    assert format_timedelta(timedelta(hours=2, minutes=30, seconds=0)) == "02:30:00"
    assert format_timedelta(timedelta(hours=23, minutes=59, seconds=59)) == "23:59:59"
    assert format_timedelta(timedelta(hours=3, minutes=15, seconds=45)) == "03:15:45"


def test_format_timedelta_exactly_24h():
    assert format_timedelta(timedelta(days=1)) == "1d 00:00:00"


def test_format_timedelta_25h30m():
    assert format_timedelta(timedelta(days=1, hours=1, minutes=30)) == "1d 01:30:00"


def test_format_timedelta_2days_plus():
    assert format_timedelta(timedelta(days=2, hours=3, minutes=5, seconds=10)) == "2d 03:05:10"


def test_format_timedelta_cross_day_fraction():
    a = datetime(2026, 8, 21, 22, 0, 0)
    b = datetime(2026, 8, 22, 1, 30, 0)
    td = safe_timediff(b, a)
    assert format_timedelta(td) == "03:30:00"


def test_format_timedelta_negative_raises_value_error():
    with pytest.raises(ValueError):
        format_timedelta(timedelta(hours=-1))


def test_format_timedelta_none():
    assert format_timedelta(None) is None


def test_same_day_diff_end_to_end():
    start = parse_datetime("2026-08-21 12:00:00")
    end = parse_datetime("2026-08-21 14:00:00")
    assert format_timedelta(safe_timediff(end, start)) == "02:00:00"


def test_format_timedelta_seconds_precision():
    start = parse_datetime("2026-08-04 16:09:12")
    end = parse_datetime("2026-08-04 16:12:45")
    td = safe_timediff(end, start)
    assert format_timedelta(td) == "00:03:33"


def test_parse_duration_to_seconds():
    from app.utils.time_utils import parse_duration_to_seconds
    assert parse_duration_to_seconds("03:19:05") == 11945.0
    assert parse_duration_to_seconds("27:15:30") == 98130.0
    assert parse_duration_to_seconds("00:01:30.500") == 90.5
    assert parse_duration_to_seconds("1d 04:00:00") == 100800.0
    assert parse_duration_to_seconds(120) == 120.0
    assert parse_duration_to_seconds(120.75) == 120.75
    assert parse_duration_to_seconds(timedelta(hours=1, minutes=30)) == 5400.0
    # Error / blank / invalid handling
    assert parse_duration_to_seconds("#VALUE!") is None
    assert parse_duration_to_seconds("#N/A") is None
    assert parse_duration_to_seconds("#REF!") is None
    assert parse_duration_to_seconds("#DIV/0!") is None
    assert parse_duration_to_seconds("") is None
    assert parse_duration_to_seconds("   ") is None
    assert parse_duration_to_seconds(None) is None
    assert parse_duration_to_seconds("null") is None
    assert parse_duration_to_seconds("nan") is None
    assert parse_duration_to_seconds("-") is None
    assert parse_duration_to_seconds("-01:00:00") is None
    assert parse_duration_to_seconds(True) is None
    assert parse_duration_to_seconds(False) is None


def test_format_duration_hhmmss():
    from app.utils.time_utils import format_duration_hhmmss
    assert format_duration_hhmmss(11945) == "03:19:05"
    assert format_duration_hhmmss(98130) == "27:15:30"
    assert format_duration_hhmmss(360005) == "100:00:05"
    assert format_duration_hhmmss(0) == "00:00:00"
    assert format_duration_hhmmss(59) == "00:00:59"
    assert format_duration_hhmmss(None) is None
    assert format_duration_hhmmss(-10) is None


def test_compute_duration_average_excel_equivalence():
    from app.utils.time_utils import compute_duration_average
    # Scenario: 4 valid values, 3 errors/blanks
    values = [
        "01:00:00",  # 3600s
        "#VALUE!",   # ignored
        "02:00:00",  # 7200s
        "",          # ignored
        "03:00:00",  # 10800s
        None,        # ignored
        "26:00:00",  # 93600s (greater than 24h)
    ]
    # Sum = 3600 + 7200 + 10800 + 93600 = 115200s
    # Count = 4 (errors and blanks excluded from denominator)
    # Average = 115200 / 4 = 28800s = 8 hours -> 08:00:00
    fmt, count, total_sum, avg_sec = compute_duration_average(values)
    assert count == 4
    assert total_sum == 115200.0
    assert avg_sec == 28800.0
    assert fmt == "08:00:00"


