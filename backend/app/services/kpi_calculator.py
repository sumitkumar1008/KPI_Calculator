"""
Row-Level KPI Calculation Engine
=================================
Calculates 5 Key Performance Indicators (KPIs) for each incident record:

1. MTTI       (Mean Time To Involve)     = AUTOMATION_END_TIME - SRCREATIONTIME
2. MTTA       (Mean Time To Allocate)    = ROSTER_ALLOCATION_TIME - SRCREATIONTIME
3. MTTAck     (Mean Time To Acknowledge) = FIRST_ACKNOWLEDGEMENT_TIME - ROSTER_ALLOCATION_TIME
4. MTTR (raw) (Mean Time To Resolve)     = RESOLVEDTIME - SRCREATIONTIME  [SRSTATUS is Closed/Resolved only]
5. MTTr       (Mean Time To Restore)     = CIRCUIT_UPTIME - SRCREATIONTIME [SUBTYPE Link Down only]

Handles Business Data Policies & Conditions:
--------------------------------------------
- MTTR Condition: Calculated ONLY when SRSTATUS is 'Closed' or 'Resolved' (case-insensitive).
  If SRSTATUS is absent, empty, or not Closed/Resolved -> KPI set to null + warning.
- MTTr Condition: Calculated ONLY when SUBTYPE is 'Link Down' (case-insensitive).
  If SUBTYPE is absent, empty, or not Link Down -> KPI set to null + warning.
- Q2 Policy (Negative Durations): End time before start time -> KPI set to null + row warning.
- Q3 Policy (Missing/Null Dates): Blank or unparseable timestamp cell -> KPI set to null + row warning.
"""

from datetime import datetime
import re
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
    "MTTr": ("CIRCUIT_UPTIME", "SRCREATIONTIME"),
}

SRSTATUS_CANDIDATES = (
    "SRSTATUS", "SR_STATUS", "SR STATUS", "STATUS", "INCIDENT_STATUS", "INCIDENT STATUS"
)
SUBTYPE_CANDIDATES = (
    "SUBTYPE", "SUB_TYPE", "SUB TYPE", "INCIDENT_SUBTYPE", "INCIDENT_SUB_TYPE", "INCIDENT SUBTYPE", "SUB-TYPE"
)


def is_srstatus_closed_or_resolved(val: Any) -> bool:
    """
    Returns True if SRSTATUS indicates the incident is Closed or Resolved (case-insensitive).
    Matches 'Closed', 'Resolved', 'closed', 'resolved', and prefixed variants like 'Closed - Completed'.
    """
    if val is None:
        return False
    s = str(val).strip().lower()
    if not s or s in ("none", "nan", "null"):
        return False
    return s in ("closed", "resolved") or s.startswith("closed") or s.startswith("resolved")


def is_subtype_link_down(val: Any) -> bool:
    """
    Returns True if SUBTYPE indicates the incident is Link Down (case-insensitive).
    Matches 'Link Down', 'link down', 'LinkDown', 'link_down', 'link-down', and variants containing 'link down'.
    """
    if val is None:
        return False
    s = str(val).strip().lower()
    if not s or s in ("none", "nan", "null"):
        return False
    norm = re.sub(r"[\s_-]+", " ", s)
    return norm == "link down" or "link down" in norm


def _get_srstatus(row: dict[str, Any]) -> str | None:
    for k in SRSTATUS_CANDIDATES:
        if k in row and row[k] is not None:
            v = str(row[k]).strip()
            if v and v.lower() not in ("none", "nan", "null"):
                return v
    return None


def _get_subtype(row: dict[str, Any]) -> str | None:
    for k in SUBTYPE_CANDIDATES:
        if k in row and row[k] is not None:
            v = str(row[k]).strip()
            if v and v.lower() not in ("none", "nan", "null"):
                return v
    return None


def _find_df_col(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    col_map = {str(col).strip().upper(): col for col in df.columns}
    for c in candidates:
        if c.upper() in col_map:
            return col_map[c.upper()]
    return None


def compute_df_kpis(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Vectorized computation of all 5 KPIs across an entire pandas DataFrame.
    Runs C-accelerated NumPy vectorized calculations in sub-millisecond execution time.
    
    Logics:
    - MTTI       = AUTOMATION_END_TIME - SRCREATIONTIME
    - MTTA       = ROSTER_ALLOCATION_TIME - SRCREATIONTIME
    - MTTAck     = FIRST_ACKNOWLEDGEMENT_TIME - ROSTER_ALLOCATION_TIME
    - MTTR (raw) = RESOLVEDTIME - SRCREATIONTIME  [SRSTATUS is Closed/Resolved only]
    - MTTr       = CIRCUIT_UPTIME - SRCREATIONTIME [SUBTYPE Link Down only]
    """
    global_warnings: list[str] = []
    
    raw_kpi_keys = {
        "MTTI": "MTTI_RAW",
        "MTTA": "MTTA_RAW",
        "MTTAck": "MTTACK_RAW",
        "MTTR": "MTTR_RAW",
        "MTTr": "MTTr_RAW",
    }

    row_warnings: list[list[str]] = [[] for _ in range(len(df))]
    
    status_col = _find_df_col(df, SRSTATUS_CANDIDATES)
    subtype_col = _find_df_col(df, SUBTYPE_CANDIDATES)
    
    for kpi_name, (end_col, start_col) in KPI_FORMULAS.items():
        sec_col = f"{kpi_name}_seconds"
        raw_key = raw_kpi_keys.get(kpi_name)
        
        # 1. Prefer pre-calculated sheet column if present
        if raw_key and raw_key in df.columns:
            raw_series = df[raw_key]
            parsed_sec = raw_series.apply(parse_duration_to_seconds)
            df[sec_col] = parsed_sec
            formatted = format_duration_series(df[sec_col])
            df[kpi_name] = formatted.where(formatted.notna(), None)
            continue

        # 2. Vectorized timestamp subtraction
        actual_start_col = start_col
        if actual_start_col not in df.columns and actual_start_col == "SRCREATIONTIME" and "CREATIONTIME" in df.columns:
            actual_start_col = "CREATIONTIME"
        elif actual_start_col not in df.columns and actual_start_col == "CREATIONTIME" and "SRCREATIONTIME" in df.columns:
            actual_start_col = "SRCREATIONTIME"

        if end_col in df.columns and actual_start_col in df.columns:
            end_dt = pd.to_datetime(df[end_col], dayfirst=True, errors="coerce")
            start_dt = pd.to_datetime(df[actual_start_col], dayfirst=True, errors="coerce")
            
            diff_sec = (end_dt - start_dt).dt.total_seconds()
            
            neg_mask = diff_sec.notna() & (diff_sec < 0)
            null_mask = end_dt.isna() | start_dt.isna()
            valid_mask = diff_sec.notna() & (diff_sec >= 0)

            # Condition: MTTR (raw) -> SRSTATUS is Closed/Resolved only
            if kpi_name == "MTTR":
                if status_col:
                    status_series = df[status_col].astype(str).str.strip().str.lower()
                    status_valid = (
                        status_series.isin(["closed", "resolved"])
                        | status_series.str.startswith("closed")
                        | status_series.str.startswith("resolved")
                    )
                else:
                    status_valid = pd.Series(False, index=df.index)
                
                invalid_status_mask = ~status_valid
                valid_mask = valid_mask & status_valid
                
                if invalid_status_mask.any():
                    s_vals = df[status_col].tolist() if status_col else [None] * len(df)
                    for idx in np.where(invalid_status_mask)[0]:
                        s_val = s_vals[idx]
                        s_disp = f"'{s_val}'" if s_val is not None and not pd.isna(s_val) else "missing/null"
                        row_warnings[idx].append(f"MTTR: SRSTATUS is {s_disp} (must be Closed/Resolved); KPI set to null")

            # Condition: MTTr -> SUBTYPE Link Down only
            if kpi_name == "MTTr":
                if subtype_col:
                    subtype_series = df[subtype_col].astype(str).str.strip().str.lower()
                    subtype_valid = subtype_series.str.contains(r"link[\s_-]*down", regex=True, na=False)
                else:
                    subtype_valid = pd.Series(False, index=df.index)

                invalid_subtype_mask = ~subtype_valid
                valid_mask = valid_mask & subtype_valid

                if invalid_subtype_mask.any():
                    sub_vals = df[subtype_col].tolist() if subtype_col else [None] * len(df)
                    for idx in np.where(invalid_subtype_mask)[0]:
                        sub_val = sub_vals[idx]
                        sub_disp = f"'{sub_val}'" if sub_val is not None and not pd.isna(sub_val) else "missing/null"
                        row_warnings[idx].append(f"MTTr: SUBTYPE is {sub_disp} (must be Link Down); KPI set to null")

            df[sec_col] = pd.Series(np.where(valid_mask, diff_sec, np.nan), index=df.index)
            formatted = format_duration_series(df[sec_col])
            df[kpi_name] = formatted.where(formatted.notna(), None)
            
            # Warn on negative duration or missing timestamps only for records that met condition
            cond_valid = pd.Series(True, index=df.index)
            if kpi_name == "MTTR":
                cond_valid = status_valid
            elif kpi_name == "MTTr":
                cond_valid = subtype_valid

            warn_neg_mask = neg_mask & cond_valid
            warn_null_mask = null_mask & cond_valid

            if warn_neg_mask.any():
                for idx in np.where(warn_neg_mask)[0]:
                    row_warnings[idx].append(f"{kpi_name}: invalid negative duration; KPI set to null")
            if warn_null_mask.any():
                for idx in np.where(warn_null_mask)[0]:
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
    Falls back to CREATIONTIME if SRCREATIONTIME is requested but missing, and vice versa.
    """
    val = row.get(col)
    if val is None and col == "CREATIONTIME":
        val = row.get("SRCREATIONTIME")
    elif val is None and col == "SRCREATIONTIME":
        val = row.get("CREATIONTIME")
    return parse_datetime(val)


def compute_row_kpis(row: dict[str, Any]) -> dict[str, Any]:
    """
    Computes all 5 KPI metrics for a single incident data row.
    
    Logics:
    - MTTI       = AUTOMATION_END_TIME - SRCREATIONTIME
    - MTTA       = ROSTER_ALLOCATION_TIME - SRCREATIONTIME
    - MTTAck     = FIRST_ACKNOWLEDGEMENT_TIME - ROSTER_ALLOCATION_TIME
    - MTTR (raw) = RESOLVEDTIME - SRCREATIONTIME  [SRSTATUS is Closed/Resolved only]
    - MTTr       = CIRCUIT_UPTIME - SRCREATIONTIME [SUBTYPE Link Down only]
    
    Args:
        row: Dictionary representing an Excel row with mapped column keys.
        
    Returns:
        dict containing:
        - "kpis": Dictionary mapping KPI_Name -> formatted string ("HH:MM:SS") or None
        - "kpi_seconds": Dictionary mapping KPI_Name -> total seconds (numeric float/int) or None
        - "warnings": List of string warnings for missing data cells, invalid status/subtype, or negative durations.
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

        # 2. Condition Check for MTTR (raw): [SRSTATUS is Closed/Resolved only]
        if kpi_name == "MTTR":
            sr_status = _get_srstatus(row)
            if not is_srstatus_closed_or_resolved(sr_status):
                kpis[kpi_name] = None
                kpi_seconds[kpi_name] = None
                status_disp = f"'{sr_status}'" if sr_status is not None else "missing/null"
                warnings.append(
                    f"MTTR: SRSTATUS is {status_disp} (must be Closed/Resolved); KPI set to null"
                )
                continue

        # 3. Condition Check for MTTr: [SUBTYPE Link Down only]
        if kpi_name == "MTTr":
            subtype = _get_subtype(row)
            if not is_subtype_link_down(subtype):
                kpis[kpi_name] = None
                kpi_seconds[kpi_name] = None
                subtype_disp = f"'{subtype}'" if subtype is not None else "missing/null"
                warnings.append(
                    f"MTTr: SUBTYPE is {subtype_disp} (must be Link Down); KPI set to null"
                )
                continue

        # 4. Compute timestamp difference: end_col - start_col
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

        # Record total non-negative duration seconds
        try:
            total_sec = get_timedelta_seconds(td)
            if total_sec is not None:
                kpis[kpi_name] = format_duration_hhmmss(total_sec)
                kpi_seconds[kpi_name] = total_sec
            else:
                kpis[kpi_name] = None
                kpi_seconds[kpi_name] = None
        except Exception as exc:
            kpis[kpi_name] = None
            kpi_seconds[kpi_name] = None
            warnings.append(f"{kpi_name}: format error: {exc}; KPI set to null")

    return {"kpis": kpis, "kpi_seconds": kpi_seconds, "warnings": warnings}
