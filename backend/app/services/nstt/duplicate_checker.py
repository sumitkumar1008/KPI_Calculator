"""
Duplicate Checker Service
=========================
Detects duplicate INCIDENTID values in the enriched dataset.
FLAGS duplicates with `is_potential_duplicate = True` without deleting any records.
"""

from typing import Any, Dict, List
import pandas as pd


def check_duplicates(df: pd.DataFrame, id_col: str = "INCIDENTID") -> Dict[str, Any]:
    """
    Scans DataFrame for duplicate values in the ID column.
    Adds boolean column `is_potential_duplicate` to DataFrame.
    Does NOT drop or delete any rows.
    
    Returns:
        {
            "df": pd.DataFrame (with is_potential_duplicate column),
            "total_records": int,
            "unique_incident_ids": int,
            "duplicate_records_count": int,
            "duplicate_incident_ids": list[str],
        }
    """
    if df is None or df.empty:
        return {
            "df": df,
            "total_records": 0,
            "unique_incident_ids": 0,
            "duplicate_records_count": 0,
            "duplicate_incident_ids": [],
        }

    df_copy = df.copy()

    if id_col not in df_copy.columns:
        df_copy["is_potential_duplicate"] = False
        return {
            "df": df_copy,
            "total_records": len(df_copy),
            "unique_incident_ids": len(df_copy),
            "duplicate_records_count": 0,
            "duplicate_incident_ids": [],
        }

    # Normalize ID series for duplicate identification
    norm_ids = df_copy[id_col].fillna("").astype(str).str.strip().str.upper()
    
    # Exclude empty/null values from being flagged as "duplicate incident IDs"
    valid_mask = norm_ids.ne("") & norm_ids.ne("NAN") & norm_ids.ne("NONE")

    # Find duplicates (keep=False marks all occurrences of duplicates as True)
    is_dup = norm_ids.duplicated(keep=False) & valid_mask
    df_copy["is_potential_duplicate"] = is_dup

    duplicate_rows_count = int(is_dup.sum())
    duplicate_ids = df_copy.loc[is_dup, id_col].fillna("").astype(str).unique().tolist()
    unique_ids_count = int(norm_ids[valid_mask].nunique())

    return {
        "df": df_copy,
        "total_records": len(df_copy),
        "unique_incident_ids": unique_ids_count,
        "duplicate_records_count": duplicate_rows_count,
        "duplicate_incident_ids": duplicate_ids,
    }
