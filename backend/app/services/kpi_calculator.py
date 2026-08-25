"""
Row-Level KPI Calculation Engine
=================================
Calculates 5 Key Performance Indicators (KPIs) for each incident record:

1. MTTI   (Mean Time To Involve)    = AUTOMATION_END_TIME - SRCREATIONTIME
2. MTTA   (Mean Time To Allocate)   = ROSTER_ALLOCATION_TIME - SRCREATIONTIME
3. MTTAck (Mean Time To Acknowledge)= FIRST_ACKNOWLEDGEMENT_TIME - ROSTER_ALLOCATION_TIME
4. MTTR   (Mean Time To Resolve)    = RESOLVEDTIME - SRCREATIONTIME
5. MTTr   (Mean Time To Restore)    = CIRCUIT_UPTIME - CREATIONTIME (or SRCREATIONTIME)

Handles Business Data Policies:
-------------------------------
- Q2 Policy (Negative Durations): End time before start time -> KPI set to null + row warning.
- Q3 Policy (Missing/Null Dates): Blank or unparseable timestamp cell -> KPI set to null + row warning.
"""

from datetime import datetime
from typing import Any

from app.utils.time_utils import format_timedelta, parse_datetime, safe_timediff

# KPI Formula Definitions: Maps KPI_Name -> (End_Timestamp_Column, Start_Timestamp_Column)
KPI_FORMULAS: dict[str, tuple[str, str]] = {
    "MTTI": ("AUTOMATION_END_TIME", "SRCREATIONTIME"),
    "MTTA": ("ROSTER_ALLOCATION_TIME", "SRCREATIONTIME"),
    "MTTAck": ("FIRST_ACKNOWLEDGEMENT_TIME", "ROSTER_ALLOCATION_TIME"),
    "MTTR": ("RESOLVEDTIME", "SRCREATIONTIME"),
    "MTTr": ("CIRCUIT_UPTIME", "CREATIONTIME"),
}


def _safe_read_dt(row: dict[str, Any], col: str) -> datetime | None:
    """
    Helper to extract and parse a datetime value from a row dictionary.
    Falls back to SRCREATIONTIME if CREATIONTIME is requested but missing.
    """
    val = row.get(col)
    if val is None and col == "CREATIONTIME":
        val = row.get("SRCREATIONTIME")
    return parse_datetime(val)


def compute_row_kpis(row: dict[str, Any]) -> dict[str, Any]:
    """
    Computes all 5 KPI metrics for a single Excel data row.
    
    Args:
        row: Dictionary representing an Excel row with mapped column keys.
        
    Returns:
        dict containing:
        - "kpis": Dictionary mapping KPI_Name -> formatted string ("HH:MM:SS" or "Xd HH:MM:SS") or None
        - "warnings": List of string warnings for missing data cells or negative durations.
    """
    kpis: dict[str, str | None] = {}
    warnings: list[str] = []

    # Iterate over each defined KPI formula
    for kpi_name, (end_col, start_col) in KPI_FORMULAS.items():
        end_dt = _safe_read_dt(row, end_col)
        start_dt = _safe_read_dt(row, start_col)

        # Q3 Policy Check: Handle missing or unparseable date cells
        if end_dt is None and start_dt is None:
            kpis[kpi_name] = None
            warnings.append(
                f"{kpi_name}: required columns '{end_col}' and '{start_col}' are missing/null; KPI set to null"
            )
            continue
        if end_dt is None:
            kpis[kpi_name] = None
            warnings.append(
                f"{kpi_name}: end column '{end_col}' is null/missing; KPI set to null"
            )
            continue
        if start_dt is None:
            kpis[kpi_name] = None
            warnings.append(
                f"{kpi_name}: start column '{start_col}' is null/missing; KPI set to null"
            )
            continue

        # Compute exact timedelta difference (end_dt - start_dt)
        td = safe_timediff(end_dt, start_dt)
        if td is None:
            kpis[kpi_name] = None
            warnings.append(f"{kpi_name}: unable to compute time difference; KPI set to null")
            continue

        # Q2 Policy Check: Handle negative duration (End timestamp < Start timestamp)
        if td.total_seconds() < 0:
            kpis[kpi_name] = None
            warnings.append(
                f"{kpi_name}: {end_col} ({end_dt.isoformat()}) is before {start_col} ({start_dt.isoformat()}); invalid negative duration; KPI set to null"
            )
            continue

        # Format timedelta into HH:MM:SS or Xd HH:MM:SS format
        try:
            kpis[kpi_name] = format_timedelta(td)
        except Exception as exc:
            kpis[kpi_name] = None
            warnings.append(f"{kpi_name}: format error: {exc}; KPI set to null")

    return {"kpis": kpis, "warnings": warnings}
