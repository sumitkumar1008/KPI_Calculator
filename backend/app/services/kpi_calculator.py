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
import numpy as np
import pandas as pd

from app.utils.time_utils import (
    format_duration_hhmmss,
    format_duration_series,
    format_timedelta,
    get_timedelta_seconds,
    parse_datetime,
    parse_duration_to_seconds,
    safe_timediff,
)

# KPI Formula Definitions: Maps KPI_Name -> (End_Timestamp_Column, Start_Timestamp_Column)
KPI_FORMULAS: dict[str, tuple[str, str]] = {
    "MTTI": ("AUTOMATION_END_TIME", "SRCREATIONTIME"),
    "MTTA": ("ROSTER_ALLOCATION_TIME", "SRCREATIONTIME"),
    "MTTAck": ("FIRST_ACKNOWLEDGEMENT_TIME", "ROSTER_ALLOCATION_TIME"),
    "MTTR": ("RESOLVEDTIME", "SRCREATIONTIME"),
    "MTTr": ("CIRCUIT_UPTIME", "CREATIONTIME"),
}


def compute_df_kpis(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Vectorized computation of all 5 KPIs across an entire pandas DataFrame.
    Runs C-accelerated NumPy vectorized calculations in sub-millisecond execution time.
    """
    global_warnings: list[str] = []
    
    raw_kpi_keys = {
        "MTTI": "MTTI_RAW",
        "MTTA": "MTTA_RAW",
        "MTTAck": "MTTACK_RAW",
        "MTTR": "MTTR_RAW",
        "MTTr": "MTTr_RAW",
    }

    if "CREATIONTIME" not in df.columns and "SRCREATIONTIME" in df.columns:
        df["CREATIONTIME"] = df["SRCREATIONTIME"]

    row_warnings: list[list[str]] = [[] for _ in range(len(df))]
    
    for kpi_name, (end_col, start_col) in KPI_FORMULAS.items():
        sec_col = f"{kpi_name}_seconds"
        raw_key = raw_kpi_keys.get(kpi_name)
        
        # 1. Prefer pre-calculated sheet column if present
        if raw_key and raw_key in df.columns:
            raw_series = df[raw_key]
            parsed_sec = raw_series.apply(parse_duration_to_seconds)
            df[sec_col] = parsed_sec
            df[kpi_name] = format_duration_series(df[sec_col])
            continue

        # 2. Vectorized timestamp subtraction fallback
        if end_col in df.columns and start_col in df.columns:
            end_dt = pd.to_datetime(df[end_col], dayfirst=True, errors="coerce")
            start_dt = pd.to_datetime(df[start_col], dayfirst=True, errors="coerce")
            
            diff_sec = (end_dt - start_dt).dt.total_seconds()
            
            neg_mask = diff_sec.notna() & (diff_sec < 0)
            null_mask = end_dt.isna() | start_dt.isna()
            valid_mask = diff_sec.notna() & (diff_sec >= 0)
            
            modulo_sec = np.where(valid_mask, diff_sec % 86400.0, np.nan)
            df[sec_col] = pd.Series(modulo_sec, index=df.index)
            df[kpi_name] = format_duration_series(df[sec_col])
            
            if neg_mask.any():
                for idx in np.where(neg_mask)[0]:
                    row_warnings[idx].append(f"{kpi_name}: invalid negative duration; KPI set to null")
            if null_mask.any():
                for idx in np.where(null_mask)[0]:
                    row_warnings[idx].append(f"{kpi_name}: required timestamp cells missing or null; KPI set to null")
        else:
            df[sec_col] = np.nan
            df[kpi_name] = None
            global_warnings.append(f"{kpi_name}: missing required columns '{end_col}' and '{start_col}'")
            for w_list in row_warnings:
                w_list.append(f"{kpi_name}: required columns missing; KPI set to null")
            
    df["warnings"] = row_warnings
    return df, global_warnings


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
        - "kpis": Dictionary mapping KPI_Name -> formatted string ("HH:MM:SS") or None
        - "kpi_seconds": Dictionary mapping KPI_Name -> total seconds (numeric float/int) or None
        - "warnings": List of string warnings for missing data cells or negative durations.
    """
    kpis: dict[str, str | None] = {}
    kpi_seconds: dict[str, float | int | None] = {}
    warnings: list[str] = []

    # Optional pre-calculated raw sheet columns mapped by excel_parser
    raw_kpi_keys: dict[str, str] = {
        "MTTI": "MTTI_RAW",
        "MTTA": "MTTA_RAW",
        "MTTAck": "MTTACK_RAW",
        "MTTR": "MTTR_RAW",
        "MTTr": "MTTr_RAW",
    }

    # Iterate over each defined KPI formula
    for kpi_name, (end_col, start_col) in KPI_FORMULAS.items():
        # 1. Check if raw Excel sheet contained pre-calculated KPI duration value
        raw_key = raw_kpi_keys.get(kpi_name)
        raw_val = row.get(raw_key) if raw_key else None

        if raw_val is not None and str(raw_val).strip() not in ("", "None", "null", "NaN", "nan"):
            sec = parse_duration_to_seconds(raw_val)
            if sec is not None:
                kpis[kpi_name] = format_duration_hhmmss(sec)
                kpi_seconds[kpi_name] = sec
                continue

        # 2. Compute timestamp difference: end_col - start_col
        end_dt = _safe_read_dt(row, end_col)
        start_dt = _safe_read_dt(row, start_col)

        # Q3 Policy Check: Handle missing or unparseable date cells
        if end_dt is None and start_dt is None:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(
                f"{kpi_name}: required columns '{end_col}' and '{start_col}' are missing/null; KPI set to null"
            )
            continue
        if end_dt is None:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(
                f"{kpi_name}: end column '{end_col}' is null/missing; KPI set to null"
            )
            continue
        if start_dt is None:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(
                f"{kpi_name}: start column '{start_col}' is null/missing; KPI set to null"
            )
            continue

        # Compute exact timedelta difference (end_dt - start_dt)
        td = safe_timediff(end_dt, start_dt)
        if td is None:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(f"{kpi_name}: unable to compute time difference; KPI set to null")
            continue

        # Q2 Policy Check: Handle negative duration (End timestamp < Start timestamp)
        if td.total_seconds() < 0:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(
                f"{kpi_name}: {end_col} ({end_dt.isoformat()}) is before {start_col} ({start_dt.isoformat()}); invalid negative duration; KPI set to null"
            )
            continue

        # 24-Hour Modulo Policy: Apply 24h modulo (duration % 86400) to match Excel hh:mm:ss formulas
        try:
            total_sec = get_timedelta_seconds(td)
            if total_sec is not None:
                modulo_sec = total_sec % 86400.0
                kpis[kpi_name] = format_duration_hhmmss(modulo_sec)
                kpi_seconds[kpi_name] = modulo_sec
            else:
                kpis[kpi_name] = None
                kpi_seconds[kpi_name] = None
        except Exception as exc:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(f"{kpi_name}: format error: {exc}; KPI set to null")

    return {"kpis": kpis, "kpi_seconds": kpi_seconds, "warnings": warnings}

