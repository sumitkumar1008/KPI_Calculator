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
    assert kpis["MTTR"] == "1d 04:00:00"
    assert kpis["MTTr"] == "2d 02:00:00"


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
