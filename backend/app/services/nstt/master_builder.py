"""
Master Response Builder Service
===============================
Converts the Final Enriched DataFrame into a canonical Master Response JSON.
Sanitizes all cell values for 100% JSON-compliance while preserving all original columns.
Optimized for low-memory footprint on Render's 512MB RAM tier.
"""

import datetime
from typing import Any, Dict, List
import numpy as np
import pandas as pd


def _sanitize_nstt_cell(val: Any) -> Any:
    """
    Sanitizes raw pandas cell values into 100% JSON-serializable Python types.
    """
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    if isinstance(val, (bool, int)):
        return val
    if isinstance(val, float):
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time, pd.Timestamp)):
        return val.isoformat()
    if hasattr(val, "item"):
        try:
            return val.item()
        except Exception:
            pass
    return str(val) if not isinstance(val, (dict, list, tuple)) else val


def build_master_response(enriched_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Constructs the canonical Master Response JSON dataset.
    Optimized single-pass construction to avoid creating duplicate intermediate dictionary lists.
    
    Args:
        enriched_df: Final enriched DataFrame containing:
                     - ALL Namo columns
                     - 5 Remedy columns (ASSIGNED_SUPPORT_COMPANY, UP_TIME, Submit Date, INCIDENT_IMPACT, DESCRIPTION)
                     - is_matched: bool
                     - is_potential_duplicate: bool
                     
    Returns:
        {
            "records": List[Dict[str, Any]],
            "total_records": int,
            "columns": List[str],
        }
    """
    if enriched_df is None or enriched_df.empty:
        return {
            "records": [],
            "total_records": 0,
            "columns": [],
        }

    # Ensure all column names are unique strings to prevent duplicate column omissions
    df_to_export = enriched_df
    if df_to_export.columns.duplicated().any():
        seen = {}
        new_cols = []
        for c in df_to_export.columns:
            c_str = str(c).strip() if c is not None and not pd.isna(c) else "UNNAMED"
            if c_str in seen:
                seen[c_str] += 1
                new_cols.append(f"{c_str}_{seen[c_str]}")
            else:
                seen[c_str] = 0
                new_cols.append(c_str)
        df_to_export = df_to_export.copy()
        df_to_export.columns = new_cols

    cols = [str(c).strip() if c is not None and not pd.isna(c) else f"UNNAMED_{i}" for i, c in enumerate(df_to_export.columns)]
    
    # Pre-identify boolean columns for fast dispatch
    bool_indices = {i for i, c in enumerate(cols) if c in ("is_matched", "is_potential_duplicate")}

    # Single-pass construction using itertuples (bypasses df.to_dict intermediate dict allocations)
    clean_records: List[Dict[str, Any]] = []
    for row in df_to_export.itertuples(index=False, name=None):
        rec: Dict[str, Any] = {}
        for idx, val in enumerate(row):
            col_name = cols[idx]
            if idx in bool_indices:
                rec[col_name] = bool(val) if val is not None and not pd.isna(val) else False
            else:
                rec[col_name] = _sanitize_nstt_cell(val)
        clean_records.append(rec)

    return {
        "records": clean_records,
        "total_records": len(clean_records),
        "columns": cols,
    }
