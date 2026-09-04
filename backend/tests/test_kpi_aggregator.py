import os
import sys
from datetime import datetime, timedelta
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.kpi_aggregator import aggregate_kpi_averages, get_period_bucket


def test_get_period_bucket_daily():
    dt = datetime(2025, 1, 15, 14, 30, 0)
    key, label, sort_dt = get_period_bucket(dt, "daily")
    assert key == "2025-01-15"
    assert label == "Jan 15, 2025"
    assert sort_dt == datetime(2025, 1, 15)


def test_get_period_bucket_weekly():
    dt = datetime(2025, 1, 15, 14, 30, 0)  # Day 15 -> Week 3
    key, label, sort_dt = get_period_bucket(dt, "weekly")
    assert key == "2025-01-W3"
    assert label == "January 2025 - Week 3"
    assert sort_dt == datetime(2025, 1, 15)



def test_get_period_bucket_monthly():
    dt = datetime(2025, 1, 15, 14, 30, 0)
    key, label, sort_dt = get_period_bucket(dt, "monthly")
    assert key == "2025-01"
    assert label == "January 2025"
    assert sort_dt == datetime(2025, 1, 1)


def test_aggregate_kpi_averages_monthly_success():
    sample_rows = [
        {
            "SRCREATIONTIME": "2025-01-10T10:00:00",
            "MTTI_seconds": 300,   # 5 mins
            "MTTA_seconds": 60,    # 1 min
            "MTTAck_seconds": 120, # 2 mins
            "MTTR_seconds": 91800, # 1d 01:30:00 (25.5 hrs)
            "MTTr_seconds": 72000, # 20 hrs
        },
        {
            "SRCREATIONTIME": "2025-01-20T14:00:00",
            "MTTI_seconds": 240,   # 4 mins
            "MTTA_seconds": 90,    # 1.5 mins
            "MTTAck_seconds": 120, # 2 mins
            "MTTR_seconds": 99000, # 1d 03:30:00 (27.5 hrs)
            "MTTr_seconds": 60000, # 16.67 hrs
        },
        {
            "SRCREATIONTIME": "2025-02-05T09:00:00",
            "MTTI_seconds": 310,
            "MTTA_seconds": 55,
            "MTTAck_seconds": 105,
            "MTTR_seconds": 76500,
            "MTTr_seconds": 54600,
        },
    ]

    res = aggregate_kpi_averages(sample_rows, group_by="monthly")

    assert res["group_by"] == "monthly"
    assert res["total_records"] == 3
    assert res["periods_count"] == 2
    assert len(res["summary"]) == 2

    # Jan 2025 summary
    jan = res["summary"][0]
    assert jan["period"] == "2025-01"
    assert jan["period_label"] == "January 2025"
    assert jan["record_count"] == 2
    assert jan["AVG_MTTI"] == "00:04:30"  # (300+240)/2 = 270s = 4m 30s
    assert jan["AVG_MTTA"] == "00:01:15"  # (60+90)/2 = 75s = 1m 15s
    assert jan["AVG_MTTAck"] == "00:02:00"
    assert jan["AVG_MTTR"] == "26:30:00" # (91800+99000)/2 = 95400s = 26.5h = 26:30:00
    assert jan["AVG_MTTr"] == "18:20:00"   # (72000+60000)/2 = 66000s = 18.33h = 18:20:00

    # Feb 2025 summary
    feb = res["summary"][1]
    assert feb["period"] == "2025-02"
    assert feb["record_count"] == 1


def test_aggregate_kpi_averages_string_fallback():
    sample_rows = [
        {
            "SRCREATIONTIME": "2025-01-10T10:00:00",
            "MTTI": "00:05:00",
            "MTTA": "00:01:00",
            "MTTAck": "00:02:00",
            "MTTR": "1d 01:30:00",
            "MTTr": "20:00:00",
        }
    ]

    res = aggregate_kpi_averages(sample_rows, group_by="monthly")
    jan = res["summary"][0]
    assert jan["AVG_MTTI"] == "00:05:00"
    assert jan["AVG_MTTR"] == "25:30:00"
