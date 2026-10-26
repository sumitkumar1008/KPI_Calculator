"""
NSTT Column Validator Service
==============================
Validates column schemas for both uploaded files upfront, independent of filenames.
Ensures fast-fail before any calculations (VLOOKUP, Rule Engine, Aggregations) are performed.
"""

import io
from typing import Any, Dict, List, Tuple
import pandas as pd

from app.services.csv_parser import parse_csv_file
from app.services.excel_parser import parse_excel_raw
from app.services.nstt.namo_reader import (
    REQUIRED_NAMO_COLUMNS,
    validate_namo_headers,
)
from app.services.nstt.remedy_reader import (
    REQUIRED_REMEDY_COLUMNS,
    validate_remedy_headers,
)


def read_raw_dataframe(file_input: Any, filename: str = "") -> Tuple[pd.DataFrame | None, List[str], str | None]:
    """
    Reads a raw DataFrame from file_input (bytes, BytesIO, or file-like object).
    Tries Excel and CSV parsing regardless of the file name.
    
    Returns:
        (df, raw_headers, error_message)
    """
    try:
        fn_lower = str(filename or "").lower()
        is_csv = fn_lower.endswith(".csv")
        is_excel = fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")

        if hasattr(file_input, "read"):
            content = file_input.read()
            if hasattr(file_input, "seek"):
                file_input.seek(0)
            bytes_target = io.BytesIO(content)
        elif isinstance(file_input, bytes):
            bytes_target = io.BytesIO(file_input)
        else:
            bytes_target = file_input

        df: pd.DataFrame | None = None

        # Try based on extension hint first if present
        if is_csv:
            df = parse_csv_file(bytes_target)
        elif is_excel:
            df = parse_excel_raw(bytes_target)

        # Fallback 1: try Excel
        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_excel_raw(bytes_target)

        # Fallback 2: try CSV
        if df is None:
            if hasattr(bytes_target, "seek"):
                bytes_target.seek(0)
            df = parse_csv_file(bytes_target)

        if df is None or len(df.columns) == 0:
            return None, [], "File is empty or contains no parseable tabular columns."

        # Ensure all column headers are clean strings
        df.columns = [
            str(c).strip() if c is not None and not pd.isna(c) else f"UNNAMED_{i}"
            for i, c in enumerate(df.columns)
        ]
        raw_headers = list(df.columns)
        return df, raw_headers, None

    except Exception as exc:
        return None, [], f"Failed to parse file: {str(exc)}"


def validate_both_files_columns(
    file1_input: Any,
    file1_name: str,
    file2_input: Any,
    file2_name: str,
) -> Dict[str, Any]:
    """
    Validates column schemas for both uploaded files upfront:
    - Slot 1 (File 1): Validated against Namo required columns:
        REQUIRED_NAMO_COLUMNS = [
            "INCIDENTID", "ATTRIBUTEDTO", "SRCREATIONTIME", "FACTORY",
            "AUTO_ALLOCATION", "AUTOMATION_UPDATE_NSTT_NUMBER", "AUTOMATION_RCA_CONCLUSION_TEXT"
        ]
    - Slot 2 (File 2): Validated against Remedy required columns:
        REQUIRED_REMEDY_COLUMNS = [
            "INCIDENT_NUMBER", "ASSIGNED_SUPPORT_COMPANY", "UP_TIME",
            "Submit Date", "INCIDENT_IMPACT", "DESCRIPTION"
        ]
    
    Validation is 100% column-based and does NOT depend upon file names.
    If there is any mismatch in either file:
    - Stops immediately (no VLOOKUP, Rule Engine, or Aggregations).
    - Throws FILE_MISMATCH error.
    - Clearly displays which columns are needed and which are missed for both files.
    """
    df1, headers1, err1 = read_raw_dataframe(file1_input, file1_name)
    df2, headers2, err2 = read_raw_dataframe(file2_input, file2_name)

    # Check unparseable files
    if err1:
        internal_err = f"File 1 ('{file1_name}') read failure: {err1}"
        return {
            "valid": False,
            "error_type": "FILE_MISMATCH",
            "error": f"File Mismatch Error: Unable to read Dataset 01 ('{file1_name}'). {err1}",
            "missing_columns": [],
            "files": {
                "file1": {
                    "slot": "Dataset 01",
                    "target_dataset": "Namo Report",
                    "filename": file1_name,
                    "status": "unparseable",
                    "missing_columns": [],
                    "found_columns": [],
                    "expected_columns": REQUIRED_NAMO_COLUMNS,
                },
                "file2": {
                    "slot": "Dataset 02",
                    "target_dataset": "Remedy Report",
                    "filename": file2_name,
                    "status": "valid" if df2 is not None else "unparseable",
                    "missing_columns": [],
                    "found_columns": headers2 if df2 is not None else [],
                    "expected_columns": REQUIRED_REMEDY_COLUMNS,
                },
            },
            "internal_error": internal_err,
        }

    if err2:
        internal_err = f"File 2 ('{file2_name}') read failure: {err2}"
        return {
            "valid": False,
            "error_type": "FILE_MISMATCH",
            "error": f"File Mismatch Error: Unable to read Dataset 02 ('{file2_name}'). {err2}",
            "missing_columns": [],
            "files": {
                "file1": {
                    "slot": "Dataset 01",
                    "target_dataset": "Namo Report",
                    "filename": file1_name,
                    "status": "valid",
                    "missing_columns": [],
                    "found_columns": headers1,
                    "expected_columns": REQUIRED_NAMO_COLUMNS,
                },
                "file2": {
                    "slot": "Dataset 02",
                    "target_dataset": "Remedy Report",
                    "filename": file2_name,
                    "status": "unparseable",
                    "missing_columns": [],
                    "found_columns": [],
                    "expected_columns": REQUIRED_REMEDY_COLUMNS,
                },
            },
            "internal_error": internal_err,
        }

    # Validate File 1 as Namo and File 2 as Remedy
    col_map1, missing_namo_1 = validate_namo_headers(headers1)
    col_map2, missing_remedy_2 = validate_remedy_headers(headers2)

    # Also check if files might be swapped
    _, remedy_missing_in_f1 = validate_remedy_headers(headers1)
    _, namo_missing_in_f2 = validate_namo_headers(headers2)

    f1_is_remedy_like = len(remedy_missing_in_f1) <= 2
    f2_is_namo_like = len(namo_missing_in_f2) <= 2

    # Case 1: Both files are completely valid!
    if len(missing_namo_1) == 0 and len(missing_remedy_2) == 0:
        renamed_namo = df1.rename(columns=col_map1)
        renamed_remedy = df2.rename(columns=col_map2)
        if "INCIDENTID" in renamed_namo.columns:
            renamed_namo["INCIDENTID"] = renamed_namo["INCIDENTID"].fillna("").astype(str).str.strip()
        if "INCIDENT_NUMBER" in renamed_remedy.columns:
            renamed_remedy["INCIDENT_NUMBER"] = renamed_remedy["INCIDENT_NUMBER"].fillna("").astype(str).str.strip()

        return {
            "valid": True,
            "namo_df": renamed_namo,
            "remedy_df": renamed_remedy,
            "namo_file_name": file1_name,
            "remedy_file_name": file2_name,
        }

    # Case 2: Column Mismatch Detected! Fast-fail before any calculations.
    error_parts: List[str] = []

    # Describe File 1 mismatch
    if missing_namo_1:
        if f1_is_remedy_like:
            error_parts.append(
                f"Dataset 01 ('{file1_name}') appears to be a Remedy Report instead of Namo Report, "
                f"missing required Namo column(s): {', '.join(missing_namo_1)}"
            )
        else:
            error_parts.append(
                f"Dataset 01 ('{file1_name}', Namo Report) is missing required column(s): {', '.join(missing_namo_1)}"
            )

    # Describe File 2 mismatch
    if missing_remedy_2:
        if f2_is_namo_like:
            error_parts.append(
                f"Dataset 02 ('{file2_name}') appears to be a Namo Report instead of Remedy Report, "
                f"missing required Remedy column(s): {', '.join(missing_remedy_2)}"
            )
        else:
            error_parts.append(
                f"Dataset 02 ('{file2_name}', Remedy Report) is missing required column(s): {', '.join(missing_remedy_2)}"
            )

    error_message = "File Mismatch Error: Required column validation failed. Please check the missing columns."

    all_missing = missing_namo_1 + missing_remedy_2

    internal_log = (
        f"================================================================================\n"
        f"[FILE MISMATCH ERROR] Column Validation Failed for Uploaded Files\n"
        f"--------------------------------------------------------------------------------\n"
        f"Checked column schemas for both uploaded files (independent of filename):\n\n"
        f"Dataset 01 (Namo Slot: '{file1_name}'):\n"
        f"  - Target Dataset: Namo Report\n"
        f"  - Status: {'MISMATCH' if missing_namo_1 else 'VALID'}\n"
        f"  - Required Columns Needed ({len(REQUIRED_NAMO_COLUMNS)}): {REQUIRED_NAMO_COLUMNS}\n"
        f"  - Missing Columns ({len(missing_namo_1)}): {missing_namo_1}\n"
        f"  - Columns Found in File ({len(headers1)}): {headers1}\n"
        f"{'  * Note: Columns found strongly match Remedy Report schema (swapped file). Dataset 01 appears to be a Remedy Report instead of Namo Report.' if f1_is_remedy_like else ''}\n\n"
        f"Dataset 02 (Remedy Slot: '{file2_name}'):\n"
        f"  - Target Dataset: Remedy Report\n"
        f"  - Status: {'MISMATCH' if missing_remedy_2 else 'VALID'}\n"
        f"  - Required Columns Needed ({len(REQUIRED_REMEDY_COLUMNS)}): {REQUIRED_REMEDY_COLUMNS}\n"
        f"  - Missing Columns ({len(missing_remedy_2)}): {missing_remedy_2}\n"
        f"  - Columns Found in File ({len(headers2)}): {headers2}\n"
        f"{'  * Note: Columns found strongly match Namo Report schema (swapped file). Dataset 02 appears to be a Namo Report instead of Remedy Report.' if f2_is_namo_like else ''}\n"
        f"--------------------------------------------------------------------------------\n"
        f"Result: Fast-fail triggered. No calculations (VLOOKUP, Rule Engine, Aggregation) performed.\n"
        f"================================================================================"
    )

    return {
        "valid": False,
        "error_type": "FILE_MISMATCH",
        "error": error_message,
        "missing_columns": all_missing,
        "files": {
            "file1": {
                "slot": "Dataset 01",
                "target_dataset": "Namo Report",
                "filename": file1_name,
                "status": "mismatch" if missing_namo_1 else "valid",
                "missing_columns": missing_namo_1,
                "found_columns": headers1,
                "expected_columns": REQUIRED_NAMO_COLUMNS,
            },
            "file2": {
                "slot": "Dataset 02",
                "target_dataset": "Remedy Report",
                "filename": file2_name,
                "status": "mismatch" if missing_remedy_2 else "valid",
                "missing_columns": missing_remedy_2,
                "found_columns": headers2,
                "expected_columns": REQUIRED_REMEDY_COLUMNS,
            },
        },
        "internal_error": internal_log,
    }
