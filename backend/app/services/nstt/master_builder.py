"""
Master Response Builder Service
===============================
Converts the Final Enriched DataFrame into a canonical Master Response JSON.
Sanitizes all cell values for 100% JSON-compliance while preserving all original columns.
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

    raw_records = enriched_df.to_dict(orient="records")
    clean_records: List[Dict[str, Any]] = []

    for rec in raw_records:
        clean_rec: Dict[str, Any] = {}
        for k, v in rec.items():
            key_str = str(k).strip() if k is not None and not pd.isna(k) else "UNNAMED"
            # Boolean metadata preserved
            if key_str in ("is_matched", "is_potential_duplicate"):
                clean_rec[key_str] = bool(v) if v is not None and not pd.isna(v) else False
            else:
                clean_rec[key_str] = _sanitize_nstt_cell(v)
        clean_records.append(clean_rec)

    cols = [str(c).strip() if c is not None and not pd.isna(c) else "UNNAMED" for c in enriched_df.columns]

    return {
        "records": clean_records,
        "total_records": len(clean_records),
        "columns": cols,
    }
