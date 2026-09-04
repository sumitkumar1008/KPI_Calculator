import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.kpi_calculator import compute_row_kpis


def test_compute_row_kpis_valid_complete_row():
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "AUTOMATION_END_TIME": datetime(2026, 8, 21, 14, 0, 0),
        "ROSTER_ALLOCATION_TIME": datetime(2026, 8, 21, 9, 0, 0),
        "FIRST_ACKNOWLEDGEMENT_TIME": datetime(2026, 8, 21, 9, 30, 0),
        "RESOLVEDTIME": datetime(2026, 8, 22, 12, 0, 0),
        "CREATIONTIME": datetime(2026, 8, 20, 10, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 22, 12, 0, 0),
    }

    result = compute_row_kpis(row)
    kpis = result["kpis"]
    warnings = result["warnings"]

    assert warnings == []
    assert kpis["MTTI"] == "06:00:00"
    assert kpis["MTTA"] == "01:00:00"
    assert kpis["MTTAck"] == "00:30:00"
    assert kpis["MTTR"] == "04:00:00"
    assert kpis["MTTr"] == "02:00:00"


def test_compute_row_kpis_missing_start_column_q3():
    row = {
        "AUTOMATION_END_TIME": datetime(2026, 8, 21, 14, 0, 0),
        # SRCREATIONTIME is missing
    }

    result = compute_row_kpis(row)
    kpis = result["kpis"]
    warnings = result["warnings"]

    assert kpis["MTTI"] is None
    assert any("SRCREATIONTIME" in w for w in warnings)


def test_compute_row_kpis_negative_duration_q2():
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 14, 0, 0),
        "AUTOMATION_END_TIME": datetime(2026, 8, 21, 8, 0, 0),  # Before start!
    }

    result = compute_row_kpis(row)
    kpis = result["kpis"]
    warnings = result["warnings"]

    assert kpis["MTTI"] is None
    assert any("invalid negative duration" in w for w in warnings)


def test_compute_row_kpis_empty_row():
    result = compute_row_kpis({})
    kpis = result["kpis"]
    warnings = result["warnings"]

    for kpi_name in ["MTTI", "MTTA", "MTTAck", "MTTR", "MTTr"]:
        assert kpis[kpi_name] is None
    assert len(warnings) == 5


def test_compute_row_kpis_with_raw_sheet_mttr():
    """Verify that when the Excel sheet has pre-calculated MTTR(raw), it is preserved exactly."""
    # Data directly from user's Excel sheet
    rows = [
        {"SRNUMBER": "40884557", "SRCREATIONTIME": "04-08-2026 15:28", "RESOLVEDTIME": "05-08-2026 16:47", "MTTR_RAW": "01:19:32"},
        {"SRNUMBER": "40884804", "SRCREATIONTIME": "04-08-2026 16:09", "RESOLVEDTIME": "05-08-2026 17:31", "MTTR_RAW": "01:21:56"},
        {"SRNUMBER": "40887115", "SRCREATIONTIME": "04-08-2026 18:11", "RESOLVEDTIME": "05-08-2026 18:25", "MTTR_RAW": "00:14:41"},
    ]
    r1 = compute_row_kpis(rows[0])
    assert r1["kpis"]["MTTR"] == "01:19:32"
    assert r1["kpi_seconds"]["MTTR"] == 4772.0

    r2 = compute_row_kpis(rows[1])
    assert r2["kpis"]["MTTR"] == "01:21:56"
    assert r2["kpi_seconds"]["MTTR"] == 4916.0

    r3 = compute_row_kpis(rows[2])
    assert r3["kpis"]["MTTR"] == "00:14:41"
    assert r3["kpi_seconds"]["MTTR"] == 881.0

