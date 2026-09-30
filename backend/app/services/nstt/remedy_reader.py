"""
Remedy File Reader Service
==========================
Parses and validates the Remedy report file (Excel/CSV).
Verifies that all 6 required Remedy columns are present.
"""

import io
import re
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.services.csv_parser import parse_csv_file
from app.services.excel_parser import parse_excel_raw


# Required columns for Remedy report
REQUIRED_REMEDY_COLUMNS = [
    "INCIDENT_NUMBER",
    "ASSIGNED_SUPPORT_COMPANY",
    "UP_TIME",
    "Submit Date",
    "INCIDENT_IMPACT",
    "DESCRIPTION",
]

# Common header aliases for robust matching
REMEDY_HEADER_ALIASES: Dict[str, List[str]] = {
    "INCIDENT_NUMBER": [
        "INCIDENT_NUMBER",
        "INCIDENT NUMBER",
        "INCIDENT_NO",
        "INCIDENT NO",
        "INCIDENTNO",
        "INCIDENTID",
        "INCIDENT_ID",
        "INCIDENT ID",
        "SRNUMBER",
        "SR_NUMBER",
    ],
    "ASSIGNED_SUPPORT_COMPANY": [
        "ASSIGNED_SUPPORT_COMPANY",
        "ASSIGNED SUPPORT COMPANY",
        "ASSIGNED_SUPPORT_COMP",
        "SUPPORT_COMPANY",
        "SUPPORT COMPANY",
        "COMPANY",
        "ASSIGNED_COMPANY",
        "ASSIGNED COMPANY",
    ],
    "UP_TIME": [
        "UP_TIME",
        "UP TIME",
        "UPTIME",
        "CIRCUIT_UPTIME",
        "CIRCUIT UPTIME",
        "RESTORED_TIME",
        "RESTORATION_TIME",
    ],
    "Submit Date": [
        "Submit Date",
        "SUBMIT_DATE",
        "SUBMIT DATE",
        "SUBMITDATE",
        "SUBMITTED_DATE",
        "SUBMITTED DATE",
        "CREATION_DATE",
        "CREATION DATE",
    ],
    "INCIDENT_IMPACT": [
        "INCIDENT_IMPACT",
        "INCIDENT IMPACT",
        "IMPACT",
        "IMPACT_TYPE",
        "IMPACT TYPE",
    ],
    "DESCRIPTION": [
        "DESCRIPTION",
        "INCIDENT_DESCRIPTION",
        "INCIDENT DESCRIPTION",
        "SUMMARY",
        "DETAILS",
        "DESC",
    ],
}


def _normalize_header(header: Any) -> str:
    """Normalizes column header for matching."""
    if header is None:
        return ""
    s = str(header).strip().upper()
    s = re.sub(r"[\s_#()-]+", "_", s)
    return s


def _build_remedy_lookup() -> Dict[str, str]:
    """Builds a lookup mapping normalized variations to canonical Remedy column names."""
    lookup: Dict[str, str] = {}
    for canonical, aliases in REMEDY_HEADER_ALIASES.items():
        lookup[_normalize_header(canonical)] = canonical
        lookup[re.sub(r"_", "", canonical.upper())] = canonical
        for alias in aliases:
            lookup[_normalize_header(alias)] = canonical
            lookup[re.sub(r"[\s_#()-]+", "", alias.upper())] = canonical
    return lookup


_REMEDY_CANONICAL_LOOKUP = _build_remedy_lookup()


def validate_remedy_headers(columns: List[Any]) -> Tuple[Dict[str, str], List[str]]:
    """
    Matches raw dataframe headers to canonical Remedy columns.
    
    Returns:
        (column_map, missing_columns)
    """
    column_map: Dict[str, str] = {}
    found_canonicals: set[str] = set()

    for raw_col in columns:
        raw_str = str(raw_col).strip()
        norm = _normalize_header(raw_str)
        norm_no_underscore = re.sub(r"[\s_#()-]+", "", raw_str.upper())

        canonical = (
            _REMEDY_CANONICAL_LOOKUP.get(norm)
            or _REMEDY_CANONICAL_LOOKUP.get(norm_no_underscore)
            or _REMEDY_CANONICAL_LOOKUP.get(raw_str.upper())
        )
        if canonical and canonical not in found_canonicals:
            column_map[raw_col] = canonical
            found_canonicals.add(canonical)

    missing_cols = [c for c in REQUIRED_REMEDY_COLUMNS if c not in found_canonicals]
    return column_map, missing_cols


def parse_remedy_file(file_input: Any, filename: str = "") -> Dict[str, Any]:
    """
    Reads and validates a Remedy Excel or CSV file.
    Renames matched required headers to canonical names.
    
    Returns:
        {
            "success": bool,
            "df": pd.DataFrame,
            "row_count": int,
            "columns": list,
            "missing_columns": list,
            "error": str (if success is False)
        }
    """
    try:
        fn_lower = str(filename).lower()
        is_csv = fn_lower.endswith(".csv")
        is_excel = fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")

        if hasattr(file_input, "read"):
            content = file_input.read()
            if hasattr(file_input, "seek"):
                file_input.seek(0)
            bytes_target: Any = io.BytesIO(content)
        else:
            bytes_target = file_input

        df: pd.DataFrame | None = None

        if is_csv:
            df = parse_csv_file(bytes_target)
        elif is_excel:
            df = parse_excel_raw(bytes_target)

        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_excel_raw(bytes_target)

        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_csv_file(bytes_target)

        if df is None or df.empty or len(df.columns) == 0:
            return {
                "success": False,
                "error": "Failed to read Remedy file: File is empty or unparseable.",
                "missing_columns": [],
                "df": None,
                "row_count": 0,
            }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to read Remedy file: {str(exc)}",
            "missing_columns": [],
            "df": None,
            "row_count": 0,
        }

    # Ensure all column headers are strings to prevent mixed type comparison errors
    df.columns = [str(c).strip() if c is not None and not pd.isna(c) else f"UNNAMED_{i}" for i, c in enumerate(df.columns)]

    raw_headers = list(df.columns)
    col_map, missing_cols = validate_remedy_headers(raw_headers)

    if missing_cols:
        missing_str = ", ".join(missing_cols)
        return {
            "success": False,
            "error": f"Remedy file missing required column(s): {missing_str}",
            "missing_columns": missing_cols,
            "df": None,
            "row_count": 0,
        }

    df_renamed = df.rename(columns=col_map)

    # Clean string columns for key identifiers
    if "INCIDENT_NUMBER" in df_renamed.columns:
        df_renamed["INCIDENT_NUMBER"] = df_renamed["INCIDENT_NUMBER"].fillna("").astype(str).str.strip()

    return {
        "success": True,
        "df": df_renamed,
        "row_count": len(df_renamed),
        "columns": list(df_renamed.columns),
        "missing_columns": [],
    }
