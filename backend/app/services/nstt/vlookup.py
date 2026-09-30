"""
VLOOKUP / Join Service
======================
Performs LEFT JOIN of Namo DataFrame with Remedy DataFrame on INCIDENTID = INCIDENT_NUMBER.
Appends ONLY the 5 required Remedy columns:
- ASSIGNED_SUPPORT_COMPANY
- UP_TIME
- Submit Date
- INCIDENT_IMPACT
- DESCRIPTION
"""

from typing import Any, Dict, List
import pandas as pd


REMEDY_APPEND_COLUMNS = [
    "ASSIGNED_SUPPORT_COMPANY",
    "UP_TIME",
    "Submit Date",
    "INCIDENT_IMPACT",
    "DESCRIPTION",
]


def perform_vlookup(namo_df: pd.DataFrame, remedy_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Performs LEFT JOIN on Namo.INCIDENTID = Remedy.INCIDENT_NUMBER.
    Preserves all Namo columns and appends the 5 required Remedy columns.
    
    Returns:
        {
            "df": pd.DataFrame (enriched),
            "total_namo_rows": int,
            "total_remedy_rows": int,
            "matched_count": int,
            "unmatched_count": int,
            "unmatched_ids": list[str],
        }
    """
    if namo_df is None or namo_df.empty:
        raise ValueError("Namo DataFrame is empty or None")
    if remedy_df is None or remedy_df.empty:
        raise ValueError("Remedy DataFrame is empty or None")

    # Make copies to prevent mutating original inputs
    namo_copy = namo_df.copy()
    remedy_copy = remedy_df.copy()

    # Create normalized join keys (strip whitespace, string conversion)
    namo_copy["_JOIN_KEY"] = namo_copy["INCIDENTID"].astype(str).str.strip().str.upper()
    remedy_copy["_JOIN_KEY"] = remedy_copy["INCIDENT_NUMBER"].astype(str).str.strip().str.upper()

    # Ensure all 5 required Remedy columns exist in remedy_df
    available_remedy_cols = ["_JOIN_KEY"]
    for col in REMEDY_APPEND_COLUMNS:
        if col in remedy_copy.columns:
            available_remedy_cols.append(col)
        else:
            remedy_copy[col] = None
            available_remedy_cols.append(col)

    # Standard VLOOKUP behavior: keep the first match per incident number
    remedy_lookup = remedy_copy[available_remedy_cols].drop_duplicates(subset=["_JOIN_KEY"], keep="first")

    # If Namo already had any of the 5 column names, drop or rename them from namo_copy before joining
    # to avoid column suffixes like '_x', '_y'
    for col in REMEDY_APPEND_COLUMNS:
        if col in namo_copy.columns and col != "INCIDENTID":
            namo_copy = namo_copy.drop(columns=[col])

    # Perform LEFT JOIN
    enriched_df = namo_copy.merge(remedy_lookup, on="_JOIN_KEY", how="left")

    # Determine matched records by checking if Remedy data joined
    matched_mask = enriched_df["_JOIN_KEY"].isin(remedy_lookup["_JOIN_KEY"])
    # Also handle empty/null incident IDs in Namo as unmatched
    valid_key_mask = enriched_df["_JOIN_KEY"].ne("") & enriched_df["_JOIN_KEY"].ne("NAN") & enriched_df["_JOIN_KEY"].ne("NONE")
    effective_matched = matched_mask & valid_key_mask

    enriched_df["is_matched"] = effective_matched

    # Clean up temporary join key
    enriched_df = enriched_df.drop(columns=["_JOIN_KEY"])

    # Identify unmatched records
    unmatched_df = enriched_df[~effective_matched]
    unmatched_ids = unmatched_df["INCIDENTID"].astype(str).unique().tolist()
    unmatched_count = len(unmatched_df)
    matched_count = int(effective_matched.sum())

    return {
        "df": enriched_df,
        "total_namo_rows": len(namo_df),
        "total_remedy_rows": len(remedy_df),
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "unmatched_ids": unmatched_ids,
    }
