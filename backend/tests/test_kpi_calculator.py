import os
import sys
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.kpi_calculator import compute_row_kpis, compute_df_kpis


def test_compute_row_kpis_valid_complete_row():
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "AUTOMATION_END_TIME": datetime(2026, 8, 21, 14, 0, 0),
        "ROSTER_ALLOCATION_TIME": datetime(2026, 8, 21, 9, 0, 0),
        "FIRST_ACKNOWLEDGEMENT_TIME": datetime(2026, 8, 21, 9, 30, 0),
        "RESOLVEDTIME": datetime(2026, 8, 22, 12, 0, 0),
        "CREATIONTIME": datetime(2026, 8, 20, 10, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 22, 12, 0, 0),
        "SRSTATUS": "Closed",
        "SUBTYPE": "Link Down",
    }

    result = compute_row_kpis(row)
    kpis = result["kpis"]
    warnings = result["warnings"]

    assert warnings == []
    assert kpis["MTTI"] == "06:00:00"
    assert kpis["MTTA"] == "01:00:00"
    assert kpis["MTTAck"] == "00:30:00"
    assert kpis["MTTR"] == "28:00:00"
    assert kpis["MTTr"] == "28:00:00"


def test_compute_row_kpis_mttr_status_resolved():
    """MTTR is calculated when SRSTATUS is 'Resolved'."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "RESOLVEDTIME": datetime(2026, 8, 21, 10, 0, 0),
        "SRSTATUS": "Resolved",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTR"] == "02:00:00"
    assert result["kpi_seconds"]["MTTR"] == 7200.0


def test_compute_row_kpis_mttr_status_case_insensitive():
    """MTTR is calculated when SRSTATUS is lowercase 'closed' or 'resolved'."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "RESOLVEDTIME": datetime(2026, 8, 21, 9, 30, 0),
        "SRSTATUS": "closed",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTR"] == "01:30:00"


def test_compute_row_kpis_mttr_status_open_not_calculated():
    """MTTR is null when SRSTATUS is 'Open'."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "RESOLVEDTIME": datetime(2026, 8, 21, 10, 0, 0),
        "SRSTATUS": "Open",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTR"] is None
    assert result["kpi_seconds"]["MTTR"] is None
    assert any("MTTR: SRSTATUS is 'Open'" in w for w in result["warnings"])


def test_compute_row_kpis_mttr_status_in_progress_not_calculated():
    """MTTR is null when SRSTATUS is 'In Progress'."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "RESOLVEDTIME": datetime(2026, 8, 21, 10, 0, 0),
        "SRSTATUS": "In Progress",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTR"] is None
    assert any("MTTR: SRSTATUS is 'In Progress'" in w for w in result["warnings"])


def test_compute_row_kpis_mttr_status_missing_not_calculated():
    """MTTR is null when SRSTATUS is missing or null."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "RESOLVEDTIME": datetime(2026, 8, 21, 10, 0, 0),
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTR"] is None
    assert any("MTTR: SRSTATUS is missing/null" in w for w in result["warnings"])


def test_compute_row_kpis_mttr_subtype_link_down():
    """MTTr is calculated when SUBTYPE is 'Link Down'."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 21, 9, 15, 0),
        "SUBTYPE": "Link Down",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTr"] == "01:15:00"
    assert result["kpi_seconds"]["MTTr"] == 4500.0


def test_compute_row_kpis_mttr_subtype_case_insensitive():
    """MTTr is calculated when SUBTYPE is 'link down' (case-insensitive)."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 21, 9, 0, 0),
        "SUBTYPE": "link down",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTr"] == "01:00:00"


def test_compute_row_kpis_mttr_subtype_primary_link_down():
    """MTTr is calculated when SUBTYPE contains 'Link Down' (e.g. 'Primary Link Down')."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 21, 9, 0, 0),
        "SUBTYPE": "Primary Link Down",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTr"] == "01:00:00"


def test_compute_row_kpis_mttr_subtype_not_link_down_not_calculated():
    """MTTr is null when SUBTYPE is not Link Down."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 21, 9, 0, 0),
        "SUBTYPE": "Interruption in Data or Network Services",
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTr"] is None
    assert result["kpi_seconds"]["MTTr"] is None
    assert any("MTTr: SUBTYPE is 'Interruption in Data or Network Services'" in w for w in result["warnings"])


def test_compute_row_kpis_mttr_subtype_missing_not_calculated():
    """MTTr is null when SUBTYPE is missing or null."""
    row = {
        "SRCREATIONTIME": datetime(2026, 8, 21, 8, 0, 0),
        "CIRCUIT_UPTIME": datetime(2026, 8, 21, 9, 0, 0),
    }
    result = compute_row_kpis(row)
    assert result["kpis"]["MTTr"] is None
    assert any("MTTr: SUBTYPE is missing/null" in w for w in result["warnings"])


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


def test_compute_df_kpis_vectorized_conditions():
    """Verify vectorized computation enforces SRSTATUS (Closed/Resolved) and SUBTYPE (Link Down)."""
    df = pd.DataFrame([
        {
            "SRCREATIONTIME": "2026-08-21 08:00:00",
            "AUTOMATION_END_TIME": "2026-08-21 14:00:00",
            "ROSTER_ALLOCATION_TIME": "2026-08-21 09:00:00",
            "FIRST_ACKNOWLEDGEMENT_TIME": "2026-08-21 09:30:00",
            "RESOLVEDTIME": "2026-08-22 12:00:00",
            "CIRCUIT_UPTIME": "2026-08-22 12:00:00",
            "SRSTATUS": "Closed",
            "SUBTYPE": "Link Down",
        },
        {
            "SRCREATIONTIME": "2026-08-21 08:00:00",
            "AUTOMATION_END_TIME": "2026-08-21 14:00:00",
            "ROSTER_ALLOCATION_TIME": "2026-08-21 09:00:00",
            "FIRST_ACKNOWLEDGEMENT_TIME": "2026-08-21 09:30:00",
            "RESOLVEDTIME": "2026-08-22 12:00:00",
            "CIRCUIT_UPTIME": "2026-08-22 12:00:00",
            "SRSTATUS": "Open",
            "SUBTYPE": "Security Issue",
        },
    ])

    res_df, global_warn = compute_df_kpis(df)
    assert global_warn == []

    # Row 0: Closed & Link Down -> MTTR and MTTr computed
    assert res_df.loc[0, "MTTI"] == "06:00:00"
    assert res_df.loc[0, "MTTA"] == "01:00:00"
    assert res_df.loc[0, "MTTAck"] == "00:30:00"
    assert res_df.loc[0, "MTTR"] == "28:00:00"
    assert res_df.loc[0, "MTTr"] == "28:00:00"

    # Row 1: Open & Security Issue -> MTTR and MTTr are null
    assert res_df.loc[1, "MTTI"] == "06:00:00"
    assert res_df.loc[1, "MTTA"] == "01:00:00"
    assert res_df.loc[1, "MTTAck"] == "00:30:00"
    assert res_df.loc[1, "MTTR"] is None
    assert pd.isna(res_df.loc[1, "MTTR_seconds"])
    assert res_df.loc[1, "MTTr"] is None
    assert pd.isna(res_df.loc[1, "MTTr_seconds"])
