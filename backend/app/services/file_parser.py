"""
Central File Parser & Common Column Service
===========================================
Contains all common column mapping rules, header normalization, required KPI columns,
date parsing, cell sanitization, and the central file parser entry point.

Delegates format reading to:
- csv_parser.py (CSV files)
- excel_parser.py (Excel .xlsx / .xls files)
- zip_parser.py (ZIP archives)
"""

import datetime
import io
import re
from typing import Any
import pandas as pd

from app.services.csv_parser import parse_csv_file
from app.services.excel_parser import parse_excel_raw
from app.services.zip_parser import parse_zip_file

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

# Accepted header name variations for SRNUMBER (Unique Identifier) in Excel/CSV sheets
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
    Normalizes raw column header strings by trimming whitespace,
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

# Optional pre-calculated KPI duration column variants present in some Excel/CSV reports
OPTIONAL_KPI_MAPPINGS: dict[str, str] = {
    "MTTR(RAW)": "MTTR_RAW",
    "MTTR (RAW)": "MTTR_RAW",
    "MTTR_RAW": "MTTR_RAW",
    "MTTR RAW": "MTTR_RAW",
    "RAW_MTTR": "MTTR_RAW",
    "MTTR": "MTTR_RAW",
    "MTTACK": "MTTACK_RAW",
    "MTTA_ACK": "MTTACK_RAW",
    "MTTA CK": "MTTACK_RAW",
    "MTT ACK": "MTTACK_RAW",
    "MTTACK(RAW)": "MTTACK_RAW",
    "MTTACK_RAW": "MTTACK_RAW",
    "MTTA_RAW": "MTTA_RAW",
    "MTTA(RAW)": "MTTA_RAW",
    "MTTA": "MTTA_RAW",
    "MTTR_CIRCUIT": "MTTr_RAW",
    "MTTR(CIRCUIT)": "MTTr_RAW",
    "MTTR (CIRCUIT)": "MTTr_RAW",
    "MTTR_CIRCUIT_UPTIME": "MTTr_RAW",
    "MTTr": "MTTr_RAW",
    "MTTI_RAW": "MTTI_RAW",
    "MTTI(RAW)": "MTTI_RAW",
    "MTTI": "MTTI_RAW",
    "AUTOMATION_RCA_CONCLUSION": "AUTOMATION_RCA_CONCLUSION",
    "AUTOMATION RCA CONCLUSION": "AUTOMATION_RCA_CONCLUSION",
    "AUTOMATION_RCA": "AUTOMATION_RCA_CONCLUSION",
    "AUTOMATION RCA": "AUTOMATION_RCA_CONCLUSION",
    "RCA_CONCLUSION": "AUTOMATION_RCA_CONCLUSION",
    "RCA CONCLUSION": "AUTOMATION_RCA_CONCLUSION",
    "AUTOMATION_RUN": "AUTOMATION_RUN",
    "AUTOMATION RUN": "AUTOMATION_RUN",
    "AUTO_RUN": "AUTOMATION_RUN",
    "AUTO RUN": "AUTOMATION_RUN",
    "AUTORUN": "AUTOMATION_RUN",
}
for k, canonical in OPTIONAL_KPI_MAPPINGS.items():
    _CANONICAL_LOOKUP[normalize_column_name(k)] = canonical
    _CANONICAL_LOOKUP[re.sub(r"[\s_#()]+", "", k.upper())] = canonical
    _CANONICAL_LOOKUP[k.upper()] = canonical


def validate_and_map_headers(columns: list[Any]) -> tuple[dict[str, str], list[str]]:
    """
    Scans raw column headers from a spreadsheet DataFrame and matches them to internal canonical column names.
    
    Args:
        columns: List of raw header string values from pandas DataFrame.
        
    Returns:
        tuple containing:
        - column_map: Dictionary mapping raw_header -> canonical_name
        - missing_columns: List of required canonical column names that were not found in file.
    """
    column_map: dict[str, str] = {}
    found_canonicals: set[str] = set()

    for raw_col in columns:
        raw_str = str(raw_col).strip()
        norm = normalize_column_name(raw_str)
        norm_no_underscore = re.sub(r"[\s_#()]+", "", raw_str.upper())

        canonical = (
            _CANONICAL_LOOKUP.get(norm)
            or _CANONICAL_LOOKUP.get(norm_no_underscore)
            or _CANONICAL_LOOKUP.get(raw_str.upper())
        )
        if canonical and canonical not in found_canonicals:
            column_map[raw_col] = canonical
            found_canonicals.add(canonical)

    # Fallback Policy: If CREATIONTIME is absent in raw headers but SRCREATIONTIME is present,
    # fallback CREATIONTIME to use SRCREATIONTIME so MTTr can still be calculated cleanly.
    if "CREATIONTIME" not in found_canonicals and "SRCREATIONTIME" in found_canonicals:
        found_canonicals.add("CREATIONTIME")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in found_canonicals]
    return column_map, missing_columns


def _sanitize_cell(val: Any) -> Any:
    """
    Sanitizes raw pandas cell values into 100% JSON-serializable Python types.
    Converts:
    - pd.isna / pd.NaT / np.nan / None -> None
    - datetime / pd.Timestamp / datetime.time / datetime.date -> ISO format string
    - numpy scalars -> native Python int/float
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time, pd.Timestamp)):
        return val.isoformat()
    if hasattr(val, "item"):
        return val.item()
    return val


def parse_file(file_input: Any, filename: str = "") -> dict[str, Any]:
    """
    Central dispatcher that inspects incoming file parameters, routes stream to the appropriate
    file parser (CSV, Excel, or ZIP), normalizes columns, and sanitizes data rows.

    Args:
        file_input: File Storage object, BytesIO buffer, filepath string, or raw bytes.
        filename: Optional filename string to hint parser selection.

    Returns:
        Dictionary result:
        - Failure: {"success": False, "error": "...", "missing_columns": [...]}
        - Success: {"success": True, "rows": [dict, ...], "row_count": int, "df": pd.DataFrame}
    """
    try:
        fn_lower = str(filename).lower()
        is_csv = fn_lower.endswith(".csv")
        is_zip = fn_lower.endswith(".zip")
        is_excel = fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")

        # Normalize stream target to BytesIO if it's a file storage or stream object
        if hasattr(file_input, "read"):
            content = file_input.read()
            if hasattr(file_input, "seek"):
                file_input.seek(0)
            bytes_target: Any = io.BytesIO(content)
        else:
            bytes_target = file_input

        df: pd.DataFrame | None = None

        if is_zip:
            df = parse_zip_file(bytes_target)
        elif is_csv:
            df = parse_csv_file(bytes_target)
        elif is_excel:
            df = parse_excel_raw(bytes_target)

        # Fallback chain if hint-based parser returned None or extension was unspecified
        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_excel_raw(bytes_target)

        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_csv_file(bytes_target)

        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_zip_file(bytes_target)

        if df is None or df.empty or len(df.columns) == 0:
            return {
                "success": False,
                "error": "Failed to read Excel file: File is empty or unparseable.",
                "missing_columns": [],
            }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to read Excel file: {str(exc)}",
            "missing_columns": [],
        }

    # Header validation & mapping
    raw_headers = list(df.columns)
    col_map, missing_cols = validate_and_map_headers(raw_headers)

    if missing_cols:
        missing_str = ", ".join(missing_cols)
        return {
            "success": False,
            "error": f"Failed to read Excel file: Missing required Excel columns: {missing_str}",
            "missing_columns": missing_cols,
        }

    # Extract mapped columns and rename to canonical required names
    df_subset = df[list(col_map.keys())].rename(columns=col_map)
    if "CREATIONTIME" not in df_subset.columns and "SRCREATIONTIME" in df_subset.columns:
        df_subset["CREATIONTIME"] = df_subset["SRCREATIONTIME"]

    # Vectorized date parsing for timestamp columns
    ts_cols = [c for c in REQUIRED_COLUMNS if c in df_subset.columns]
    for c in ts_cols:
        try:
            df_subset[c] = pd.to_datetime(
                df_subset[c],
                dayfirst=True,
                errors="coerce",
            )
        except Exception:
            pass

    raw_records = df_subset.to_dict(orient="records")
    clean_rows = []
    for record in raw_records:
        r = {k: _sanitize_cell(v) for k, v in record.items()}
        if "AUTOMATION_RCA_CONCLUSION" not in r:
            r["AUTOMATION_RCA_CONCLUSION"] = None
        if "AUTOMATION_RUN" not in r:
            r["AUTOMATION_RUN"] = None
        clean_rows.append(r)

    return {
        "success": True,
        "rows": clean_rows,
        "row_count": len(clean_rows),
        "df": df_subset,
    }
