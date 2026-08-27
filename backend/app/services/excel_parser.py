"""
Excel File Ingestion & Flexible Header Parser Service
=====================================================
Handles reading both modern (.xlsx) and legacy binary (.xls) Excel files using openpyxl & xlrd.
Normalizes incoming column names (handling case variations, spaces, underscores, hashes),
maps them to canonical internal names, and validates the presence of required KPI columns.
"""

import io
import re
from typing import Any
import pandas as pd

# Standard required timestamp columns for KPI calculations
REQUIRED_COLUMNS: list[str] = [
    "SRCREATIONTIME",             # Creation time of ticket/service request
    "AUTOMATION_END_TIME",        # End time of automated triage/processing (for MTTI)
    "ROSTER_ALLOCATION_TIME",     # Time engineer was allocated (for MTTA & MTTAck)
    "FIRST_ACKNOWLEDGEMENT_TIME", # Time engineer acknowledged ticket (for MTTAck)
    "RESOLVEDTIME",               # Time ticket was resolved (for MTTR)
    "CREATIONTIME",               # Circuit creation time (for MTTr)
    "CIRCUIT_UPTIME",             # Circuit uptime restoration time (for MTTr)
]

# Accepted header name variations for SRNUMBER (Unique Identifier) in Excel sheets
SR_NUMBER_VARIANTS: list[str] = [
    "SRNUMBER",
    "SR_NUMBER",
    "SR NUMBER",
    "SRNUM",
    "SR_NUM",
    "SR NUM",
    "SR#",
    "SR_NO",
    "SR NO",
    "SRNO",
    "INCIDENT_NUMBER",
    "INCIDENT NUMBER",
    "INCIDENTNO",
]


def normalize_column_name(col: Any) -> str:
    """
    Normalizes raw Excel column header strings by trimming whitespace,
    converting to UPPERCASE, and replacing spaces/hashes/underscores with a single underscore.
    Example: ' Automation End Time ' -> 'AUTOMATION_END_TIME'
    """
    if col is None:
        return ""
    s = str(col).strip().upper()
    s = re.sub(r"[\s_#]+", "_", s)
    return s


# Build lookup map from normalized string variations -> exact canonical column name
_CANONICAL_LOOKUP: dict[str, str] = {
    normalize_column_name(c): c for c in REQUIRED_COLUMNS
}
# Add variants without underscores (e.g. AUTOMATIONENDTIME) for maximum parsing flexibility
for c in REQUIRED_COLUMNS:
    _CANONICAL_LOOKUP[re.sub(r"_", "", c.upper())] = c

# Register all SRNUMBER variants in the canonical lookup
for var in SR_NUMBER_VARIANTS:
    _CANONICAL_LOOKUP[normalize_column_name(var)] = "SRNUMBER"
    _CANONICAL_LOOKUP[re.sub(r"[\s_#]+", "", var.upper())] = "SRNUMBER"


def validate_and_map_headers(columns: list[Any]) -> tuple[dict[str, str], list[str]]:
    """
    Scans raw column headers from an Excel file and matches them to internal canonical column names.
    
    Args:
        columns: List of raw header string values from pandas DataFrame.
        
    Returns:
        tuple containing:
        - column_map: Dictionary mapping raw_header -> canonical_name
        - missing_columns: List of required canonical column names that were not found in Excel file.
    """
    column_map: dict[str, str] = {}
    found_canonicals: set[str] = set()

    for raw_col in columns:
        norm = normalize_column_name(raw_col)
        norm_no_underscore = re.sub(r"[\s_#]+", "", str(raw_col).strip().upper())

        canonical = _CANONICAL_LOOKUP.get(norm) or _CANONICAL_LOOKUP.get(norm_no_underscore)
        if canonical and canonical not in found_canonicals:
            column_map[raw_col] = canonical
            found_canonicals.add(canonical)

    # Fallback Policy: If CREATIONTIME is absent in raw Excel headers but SRCREATIONTIME is present,
    # fallback CREATIONTIME to use SRCREATIONTIME so MTTr can still be calculated cleanly.
    if "CREATIONTIME" not in found_canonicals and "SRCREATIONTIME" in found_canonicals:
        found_canonicals.add("CREATIONTIME")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in found_canonicals]
    return column_map, missing_columns


def parse_excel_file(file_input: Any) -> dict[str, Any]:
    """
    Multi-engine Excel parser supporting modern (.xlsx via openpyxl) and legacy binary (.xls via xlrd).
    
    Args:
        file_input: File Storage object, BytesIO buffer, or filepath string.
        
    Returns:
        Dictionary result:
        - Failure: {"success": False, "error": "...", "missing_columns": [...]}
        - Success: {"success": True, "rows": [dict, ...], "row_count": int}
    """
    try:
        if hasattr(file_input, "read"):
            # Handle File Storage or BytesIO streams
            content = file_input.read()
            if hasattr(file_input, "seek"):
                file_input.seek(0)
            bytes_io = io.BytesIO(content)
            
            # Engine Fallback: Try openpyxl first (.xlsx), then xlrd (.xls), then default pandas reader
            try:
                df = pd.read_excel(bytes_io, engine="openpyxl")
            except Exception:
                bytes_io.seek(0)
                try:
                    df = pd.read_excel(bytes_io, engine="xlrd")
                except Exception:
                    bytes_io.seek(0)
                    df = pd.read_excel(bytes_io)
        else:
            try:
                df = pd.read_excel(file_input, engine="openpyxl")
            except Exception:
                try:
                    df = pd.read_excel(file_input, engine="xlrd")
                except Exception:
                    df = pd.read_excel(file_input)
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to read Excel file: {str(exc)}",
            "missing_columns": [],
        }

    raw_headers = list(df.columns)
    col_map, missing_cols = validate_and_map_headers(raw_headers)

    # Return error response if any required timestamp column is missing
    if missing_cols:
        missing_str = ", ".join(missing_cols)
        return {
            "success": False,
            "error": f"Missing required Excel columns: {missing_str}",
            "missing_columns": missing_cols,
        }

    # Extract mapped columns and rename to canonical required names
    df_subset = df[list(col_map.keys())].rename(columns=col_map)
    if "CREATIONTIME" not in df_subset.columns and "SRCREATIONTIME" in df_subset.columns:
        df_subset["CREATIONTIME"] = df_subset["SRCREATIONTIME"]

    # Convert all pandas NaN, NaT, and null values to clean Python None objects
    df_subset = df_subset.where(pd.notnull(df_subset), None)
    rows = df_subset.to_dict(orient="records")

    return {
        "success": True,
        "rows": rows,
        "row_count": len(rows),
    }
