"""
Namo File Reader Service
========================
Parses and validates the Namo report file (Excel/CSV).
Preserves ALL original Namo columns while verifying required fields.
"""

import io
import re
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.services.csv_parser import parse_csv_file
from app.services.excel_parser import parse_excel_raw


# Required columns for Namo report
REQUIRED_NAMO_COLUMNS = [
    "INCIDENTID",
    "ATTRIBUTEDTO",
    "SRCREATIONTIME",
    "FACTORY",
    "AUTO_ALLOCATION",
    "AUTOMATION_UPDATE_NSTT_NUMBER",
    "AUTOMATION_RCA_CONCLUSION_TEXT",
]

# Common header aliases for robust case/whitespace/separator matching
NAMO_HEADER_ALIASES: Dict[str, List[str]] = {
    "INCIDENTID": [
        "INCIDENTID",
        "INCIDENT_ID",
        "INCIDENT ID",
        "INCIDENT_NUMBER",
        "INCIDENT NUMBER",
        "INCIDENTNO",
        "INCIDENT_NO",
        "INCIDENT NO",
    ],
    "SRNUMBER": [
        "SRNUMBER",
        "SR_NUMBER",
        "SR NUMBER",
        "SR_NO",
        "SR NO",
        "SRNO",
        "SERVICE_REQUEST_NUMBER",
        "SERVICE REQUEST NUMBER",
    ],
    "ATTRIBUTEDTO": [
        "ATTRIBUTEDTO",
        "ATTRIBUTED_TO",
        "ATTRIBUTED TO",
        "ATTRIBUTION",
        "ATTRIBUTED",
    ],
    "SRCREATIONTIME": [
        "SRCREATIONTIME",
        "SR_CREATION_TIME",
        "SR CREATION TIME",
        "SRCREATION_TIME",
        "CREATION_TIME",
        "CREATION TIME",
        "CREATIONTIME",
        "SUBMIT_DATE",
        "SUBMIT DATE",
    ],
    "FACTORY": [
        "FACTORY",
        "FACTORY_NAME",
        "FACTORY NAME",
        "FACTORY_TYPE",
    ],
    "AUTO_ALLOCATION": [
        "AUTO_ALLOCATION",
        "AUTO ALLOCATION",
        "AUTOALLOCATION",
        "AUTOMATED_ALLOCATION",
    ],
    "AUTOMATION_UPDATE_NSTT_NUMBER": [
        "AUTOMATION_UPDATE_NSTT_NUMBER",
        "AUTOMATION UPDATE NSTT NUMBER",
        "AUTOMATION_NSTT_NUMBER",
        "AUTOMATION NSTT NUMBER",
        "UPDATE_NSTT_NUMBER",
        "UPDATE NSTT NUMBER",
        "AUTOMATIONUPDATE_NSTTNUMBER",
        "NSTT_NUMBER",
        "NSTT NUMBER",
    ],
    "AUTOMATION_RCA_CONCLUSION_TEXT": [
        "AUTOMATION_RCA_CONCLUSION_TEXT",
        "AUTOMATION RCA CONCLUSION TEXT",
        "AUTOMATION_RCA_CONCLUSION",
        "AUTOMATION RCA CONCLUSION",
        "RCA_CONCLUSION_TEXT",
        "RCA CONCLUSION TEXT",
        "RCA_CONCLUSION",
        "RCA CONCLUSION",
    ],
}


def _normalize_header(header: Any) -> str:
    """Normalizes column header for matching."""
    if header is None:
        return ""
    s = str(header).strip().upper()
    s = re.sub(r"[\s_#()-]+", "_", s)
    return s


def _build_namo_lookup() -> Dict[str, str]:
    """Builds a lookup mapping normalized variations to canonical Namo column names."""
    lookup: Dict[str, str] = {}
    for canonical, aliases in NAMO_HEADER_ALIASES.items():
        lookup[_normalize_header(canonical)] = canonical
        lookup[re.sub(r"_", "", canonical.upper())] = canonical
        for alias in aliases:
            lookup[_normalize_header(alias)] = canonical
            lookup[re.sub(r"[\s_#()-]+", "", alias.upper())] = canonical
    return lookup


_NAMO_CANONICAL_LOOKUP = _build_namo_lookup()


def validate_namo_headers(columns: List[Any]) -> Tuple[Dict[str, str], List[str]]:
    """
    Matches raw dataframe headers to canonical Namo columns.
    
    Returns:
        (column_map, missing_columns)
        column_map maps raw column names to canonical names.
    """
    column_map: Dict[str, str] = {}
    found_canonicals: set[str] = set()

    for raw_col in columns:
        raw_str = str(raw_col).strip()
        norm = _normalize_header(raw_str)
        norm_no_underscore = re.sub(r"[\s_#()-]+", "", raw_str.upper())

        canonical = (
            _NAMO_CANONICAL_LOOKUP.get(norm)
            or _NAMO_CANONICAL_LOOKUP.get(norm_no_underscore)
            or _NAMO_CANONICAL_LOOKUP.get(raw_str.upper())
        )
        if canonical and canonical not in found_canonicals:
            column_map[raw_col] = canonical
            found_canonicals.add(canonical)

    # Fallback: if INCIDENTID not found, check if a column mapped to SRNUMBER exists
    if "INCIDENTID" not in found_canonicals:
        for raw_col, can in list(column_map.items()):
            if can == "SRNUMBER":
                column_map[raw_col] = "INCIDENTID"
                found_canonicals.add("INCIDENTID")
                break

    missing_cols = [c for c in REQUIRED_NAMO_COLUMNS if c not in found_canonicals]
    return column_map, missing_cols


def parse_namo_file(file_input: Any, filename: str = "") -> Dict[str, Any]:
    """
    Reads and validates a Namo Excel or CSV file.
    Preserves ALL original Namo columns, renaming only matched required headers to canonical names.
    
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
                "error": "Failed to read Namo file: File is empty or unparseable.",
                "missing_columns": [],
                "df": None,
                "row_count": 0,
            }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to read Namo file: {str(exc)}",
            "missing_columns": [],
            "df": None,
            "row_count": 0,
        }

    # Ensure all column headers are strings to prevent mixed type comparison errors
    df.columns = [str(c).strip() if c is not None and not pd.isna(c) else f"UNNAMED_{i}" for i, c in enumerate(df.columns)]

    raw_headers = list(df.columns)
    col_map, missing_cols = validate_namo_headers(raw_headers)

    if missing_cols:
        # Check if the uploaded file is actually a Remedy report
        from app.services.nstt.remedy_reader import validate_remedy_headers
        _, remedy_missing = validate_remedy_headers(raw_headers)
        if len(remedy_missing) <= 2:
            return {
                "success": False,
                "error_type": "FILE_MISMATCH",
                "error": "File Mismatch Error (Dataset 01): The file uploaded as 'Namo Report' appears to be a Remedy Report.",
                "dataset": "Dataset 01 (Namo Report)",
                "missing_columns": missing_cols,
                "found_columns": raw_headers,
                "expected_columns": REQUIRED_NAMO_COLUMNS,
                "df": None,
                "row_count": 0,
            }

        return {
            "success": False,
            "error_type": "FILE_MISMATCH",
            "error": "File Mismatch Error (Dataset 01 - Namo Report): Uploaded file is missing required column(s).",
            "dataset": "Dataset 01 (Namo Report)",
            "missing_columns": missing_cols,
            "found_columns": raw_headers,
            "expected_columns": REQUIRED_NAMO_COLUMNS,
            "df": None,
            "row_count": 0,
        }

    # Rename matched headers to canonical names while keeping ALL other columns
    df_renamed = df.rename(columns=col_map)

    # Clean string columns for key identifiers
    if "INCIDENTID" in df_renamed.columns:
        df_renamed["INCIDENTID"] = df_renamed["INCIDENTID"].fillna("").astype(str).str.strip()

    return {
        "success": True,
        "df": df_renamed,
        "row_count": len(df_renamed),
        "columns": list(df_renamed.columns),
        "missing_columns": [],
    }
