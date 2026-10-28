"""
NSTT File Validator Service
===========================
Fast pre-validation of uploaded Namo and Remedy datasets.
Detects swapped files, mismatched schemas, and missing columns immediately
BEFORE running expensive VLOOKUP joins or Rule Engine calculations.
"""

from __future__ import annotations

import csv
import io
import os
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from app.services.nstt.namo_reader import (
    REQUIRED_NAMO_COLUMNS,
    validate_namo_headers,
)
from app.services.nstt.remedy_reader import (
    REQUIRED_REMEDY_COLUMNS,
    validate_remedy_headers,
)


def extract_file_headers(file_input: Any, filename: str = "") -> List[str]:
    """
    Fast extraction of column headers from CSV, Excel, or ZIP files without reading all rows.
    Scans the first 6 rows to detect true headers even when preceded by title/metadata banners.
    Resets the file pointer to 0 after reading.
    """
    if file_input is None:
        return []

    # Read bytes from file_input
    content: bytes = b""
    try:
        if hasattr(file_input, "read"):
            if hasattr(file_input, "seek"):
                file_input.seek(0)
            content = file_input.read()
            if hasattr(file_input, "seek"):
                file_input.seek(0)
        elif isinstance(file_input, bytes):
            content = file_input
        elif isinstance(file_input, io.BytesIO):
            content = file_input.getvalue()
    except Exception:
        return []

    if not content:
        return []

    fn_lower = str(filename or getattr(file_input, "filename", "") or "").lower()
    is_csv = fn_lower.endswith(".csv")
    is_excel = fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls")
    is_zip = fn_lower.endswith(".zip")

    # 1. ZIP archive inspection
    if is_zip or (content.startswith(b"PK\x03\x04") and not is_excel):
        try:
            with zipfile.ZipFile(io.BytesIO(content), "r") as zf:
                for member_name in zf.namelist():
                    if member_name.endswith("/") or member_name.endswith("\\"):
                        continue
                    base = os.path.basename(member_name)
                    if base.startswith(".") or "__MACOSX" in member_name:
                        continue
                    ext = os.path.splitext(base)[1].lower()
                    if ext in (".csv", ".xlsx", ".xls", ".txt"):
                        member_bytes = zf.read(member_name)
                        inner_headers = extract_file_headers(member_bytes, base)
                        if inner_headers and len(inner_headers) > 1:
                            return inner_headers
        except Exception:
            pass

    def score_headers(headers: List[str]) -> int:
        if not headers or len(headers) <= 1:
            return 0
        map_n, _ = validate_namo_headers(headers)
        map_r, _ = validate_remedy_headers(headers)
        return max(len(map_n), len(map_r))

    best_headers: List[str] = []
    best_score = 0

    # 2. Try CSV fast path (with multi-encoding and multi-delimiter)
    if is_csv or (not is_excel and not is_zip):
        for enc in ["utf-8-sig", "latin1", "cp1252"]:
            try:
                text_sample = content[:32768].decode(enc, errors="replace")
                lines = [ln.strip() for ln in text_sample.splitlines() if ln.strip()]
                for line in lines[:6]:
                    for sep in [",", ";", "\t", "|"]:
                        reader = csv.reader([line], delimiter=sep)
                        hdrs = next(reader, [])
                        hdrs = [str(h).strip() for h in hdrs if h is not None and str(h).strip()]
                        sc = score_headers(hdrs)
                        if sc > best_score:
                            best_score = sc
                            best_headers = hdrs
                            if best_score >= 3:
                                return best_headers
                        elif not best_headers and len(hdrs) > 1:
                            best_headers = hdrs
            except Exception:
                pass
        if best_headers:
            return best_headers

    # 3. Try Excel fast path (reading first 6 rows with header=None to detect title banners)
    try:
        df_head = pd.read_excel(io.BytesIO(content), nrows=6, header=None)
        if df_head is not None and not df_head.empty:
            for r_idx in range(min(6, len(df_head))):
                hdrs = [str(c).strip() for c in df_head.iloc[r_idx].values if c is not None and not pd.isna(c) and str(c).strip()]
                sc = score_headers(hdrs)
                if sc > best_score:
                    best_score = sc
                    best_headers = hdrs
                    if best_score >= 3:
                        return best_headers
                elif not best_headers and len(hdrs) > 1:
                    best_headers = hdrs
        if best_headers:
            return best_headers
    except Exception:
        pass

    try:
        df_head = pd.read_excel(io.BytesIO(content), nrows=0)
        hdrs = [str(c).strip() for c in df_head.columns if c is not None and not pd.isna(c) and str(c).strip()]
        if hdrs:
            return hdrs
    except Exception:
        pass

    # 4. Fallback CSV with pandas
    try:
        df_csv = pd.read_csv(io.BytesIO(content), nrows=0, encoding_errors="replace")
        hdrs = [str(c).strip() for c in df_csv.columns if c is not None and not pd.isna(c) and str(c).strip()]
        if hdrs:
            return hdrs
    except Exception:
        pass

    return best_headers


def validate_nstt_uploads(
    namo_file_input: Any,
    remedy_file_input: Any,
    namo_filename: str = "",
    remedy_filename: str = "",
) -> Dict[str, Any]:
    """
    Validates both Namo and Remedy files for schema correctness and detects swapped files.

    Returns:
        {
            "valid": bool,
            "error_type": "SWAPPED_FILES" | "WRONG_FILE_IN_NAMO" | "WRONG_FILE_IN_REMEDY" | "MISSING_COLUMNS" | None,
            "title": str,
            "message": str,
            "recommendation": str,
            "can_auto_swap": bool,
            "namo_slot": {
                "filename": str,
                "valid": bool,
                "detected_as": str,
                "missing_columns": list[str],
                "required_columns": list[str],
            },
            "remedy_slot": {
                "filename": str,
                "valid": bool,
                "detected_as": str,
                "missing_columns": list[str],
                "required_columns": list[str],
            }
        }
    """
    namo_fn = namo_filename or getattr(namo_file_input, "filename", "Namo Report")
    remedy_fn = remedy_filename or getattr(remedy_file_input, "filename", "Remedy Report")

    headers_namo_slot = extract_file_headers(namo_file_input, namo_fn) if namo_file_input else []
    headers_remedy_slot = extract_file_headers(remedy_file_input, remedy_fn) if remedy_file_input else []

    # Check Slot 1 against Namo & Remedy schemas
    _, missing_namo_in_slot1 = validate_namo_headers(headers_namo_slot)
    _, missing_remedy_in_slot1 = validate_remedy_headers(headers_namo_slot)

    # Check Slot 2 against Remedy & Namo schemas
    _, missing_remedy_in_slot2 = validate_remedy_headers(headers_remedy_slot)
    _, missing_namo_in_slot2 = validate_namo_headers(headers_remedy_slot)

    # Heuristics for detection:
    # A slot is considered a Remedy file if it satisfies Remedy required columns (0 missing) or <= 1 missing
    slot1_is_remedy = len(headers_namo_slot) > 0 and len(missing_remedy_in_slot1) <= 1 and len(missing_namo_in_slot1) >= 4
    # A slot is considered a Namo file if it satisfies Namo required columns (0 missing) or <= 1 missing
    slot2_is_namo = len(headers_remedy_slot) > 0 and len(missing_namo_in_slot2) <= 1 and len(missing_remedy_in_slot2) >= 3

    slot1_valid_namo = len(headers_namo_slot) > 0 and len(missing_namo_in_slot1) == 0
    slot2_valid_remedy = len(headers_remedy_slot) > 0 and len(missing_remedy_in_slot2) == 0

    has_file1 = namo_file_input is not None
    has_file2 = remedy_file_input is not None

    # Single-file check (when user selects or drops only one file so far)
    if has_file1 and not has_file2:
        if slot1_is_remedy:
            return {
                "valid": False,
                "error_type": "WRONG_FILE_IN_NAMO",
                "title": "Wrong File in Namo Slot (Dataset 01)",
                "message": f"The file '{namo_fn}' uploaded in the Namo Report section matches the Remedy Report format. It is missing required Namo columns.",
                "recommendation": "Please upload the correct Namo Report in Dataset 01, or place this file into Dataset 02.",
                "can_auto_swap": False,
                "namo_slot": {
                    "filename": namo_fn,
                    "valid": False,
                    "detected_as": "Remedy Report",
                    "missing_columns": missing_namo_in_slot1,
                    "required_columns": REQUIRED_NAMO_COLUMNS,
                },
                "remedy_slot": None,
            }
        elif slot1_valid_namo:
            return {
                "valid": True,
                "error_type": None,
                "title": "Namo Report Verified",
                "message": f"'{namo_fn}' verified as valid Namo Report.",
                "recommendation": "Please upload Remedy Report to proceed with calculation.",
                "can_auto_swap": False,
                "namo_slot": {
                    "filename": namo_fn,
                    "valid": True,
                    "detected_as": "Namo Report",
                    "missing_columns": [],
                    "required_columns": REQUIRED_NAMO_COLUMNS,
                },
                "remedy_slot": None,
            }
        else:
            return {
                "valid": False,
                "error_type": "MISSING_COLUMNS",
                "title": "Invalid Namo Report Schema",
                "message": f"'{namo_fn}' is missing {len(missing_namo_in_slot1)} mandatory Namo column(s).",
                "recommendation": "Please upload a valid Namo Report file.",
                "can_auto_swap": False,
                "namo_slot": {
                    "filename": namo_fn,
                    "valid": False,
                    "detected_as": "Invalid / Unknown Format",
                    "missing_columns": missing_namo_in_slot1,
                    "required_columns": REQUIRED_NAMO_COLUMNS,
                },
                "remedy_slot": None,
            }

    if has_file2 and not has_file1:
        if slot2_is_namo:
            return {
                "valid": False,
                "error_type": "WRONG_FILE_IN_REMEDY",
                "title": "Wrong File in Remedy Slot (Dataset 02)",
                "message": f"The file '{remedy_fn}' uploaded in the Remedy Report section matches the Namo Report format. It is missing required Remedy columns.",
                "recommendation": "Please upload the correct Remedy Report in Dataset 02, or place this file into Dataset 01.",
                "can_auto_swap": False,
                "namo_slot": None,
                "remedy_slot": {
                    "filename": remedy_fn,
                    "valid": False,
                    "detected_as": "Namo Report",
                    "missing_columns": missing_remedy_in_slot2,
                    "required_columns": REQUIRED_REMEDY_COLUMNS,
                },
            }
        elif slot2_valid_remedy:
            return {
                "valid": True,
                "error_type": None,
                "title": "Remedy Report Verified",
                "message": f"'{remedy_fn}' verified as valid Remedy Report.",
                "recommendation": "Please upload Namo Report to proceed with calculation.",
                "can_auto_swap": False,
                "namo_slot": None,
                "remedy_slot": {
                    "filename": remedy_fn,
                    "valid": True,
                    "detected_as": "Remedy Report",
                    "missing_columns": [],
                    "required_columns": REQUIRED_REMEDY_COLUMNS,
                },
            }
        else:
            return {
                "valid": False,
                "error_type": "MISSING_COLUMNS",
                "title": "Invalid Remedy Report Schema",
                "message": f"'{remedy_fn}' is missing {len(missing_remedy_in_slot2)} mandatory Remedy column(s).",
                "recommendation": "Please upload a valid Remedy Report file.",
                "can_auto_swap": False,
                "namo_slot": None,
                "remedy_slot": {
                    "filename": remedy_fn,
                    "valid": False,
                    "detected_as": "Invalid / Unknown Format",
                    "missing_columns": missing_remedy_in_slot2,
                    "required_columns": REQUIRED_REMEDY_COLUMNS,
                },
            }

    # Both files present
    if slot1_valid_namo and slot2_valid_remedy:
        return {
            "valid": True,
            "error_type": None,
            "title": "Files Verified",
            "message": "Both datasets match their required schemas.",
            "recommendation": "",
            "can_auto_swap": False,
            "namo_slot": {
                "filename": namo_fn,
                "valid": True,
                "detected_as": "Namo Report",
                "missing_columns": [],
                "required_columns": REQUIRED_NAMO_COLUMNS,
            },
            "remedy_slot": {
                "filename": remedy_fn,
                "valid": True,
                "detected_as": "Remedy Report",
                "missing_columns": [],
                "required_columns": REQUIRED_REMEDY_COLUMNS,
            },
        }

    # Error classification
    can_auto_swap = False
    if slot1_is_remedy and slot2_is_namo:
        error_type = "SWAPPED_FILES"
        title = "Wrong Files Uploaded: Datasets Are Swapped"
        message = (
            f"It appears '{namo_fn}' is a Remedy Report and '{remedy_fn}' is a Namo Report. "
            "The files were uploaded into swapped sections."
        )
        recommendation = "Please re-upload the files into their respective upload zones, or use 'Swap Files' to switch them automatically."
        can_auto_swap = True
    elif slot1_is_remedy:
        error_type = "WRONG_FILE_IN_NAMO"
        title = "Wrong File in Namo Slot (Dataset 01)"
        message = (
            f"The file '{namo_fn}' uploaded in the Namo Report section matches the Remedy Report format. "
            "It is missing required Namo columns."
        )
        recommendation = "Please re-upload the Namo Report file in Dataset 01."
    elif slot2_is_namo:
        error_type = "WRONG_FILE_IN_REMEDY"
        title = "Wrong File in Remedy Slot (Dataset 02)"
        message = (
            f"The file '{remedy_fn}' uploaded in the Remedy Report section matches the Namo Report format. "
            "It is missing required Remedy columns."
        )
        recommendation = "Please re-upload the Remedy Report file in Dataset 02."
    else:
        error_type = "MISSING_COLUMNS"
        title = "Wrong Files or Missing Columns Detected"
        missing_parts = []
        if not slot1_valid_namo:
            missing_parts.append(f"Namo slot missing {len(missing_namo_in_slot1)} column(s)")
        if not slot2_valid_remedy:
            missing_parts.append(f"Remedy slot missing {len(missing_remedy_in_slot2)} column(s)")
        message = f"Uploaded files cannot be processed: {'; '.join(missing_parts)}."
        recommendation = "Please re-upload the correct files with all mandatory columns."

    detected_slot1 = "Remedy Report" if slot1_is_remedy else ("Namo Report" if slot1_valid_namo else "Invalid / Unknown Format")
    detected_slot2 = "Namo Report" if slot2_is_namo else ("Remedy Report" if slot2_valid_remedy else "Invalid / Unknown Format")

    return {
        "valid": False,
        "error_type": error_type,
        "title": title,
        "message": message,
        "recommendation": recommendation,
        "can_auto_swap": can_auto_swap,
        "namo_slot": {
            "filename": namo_fn,
            "valid": slot1_valid_namo,
            "detected_as": detected_slot1,
            "missing_columns": missing_namo_in_slot1,
            "required_columns": REQUIRED_NAMO_COLUMNS,
        },
        "remedy_slot": {
            "filename": remedy_fn,
            "valid": slot2_valid_remedy,
            "detected_as": detected_slot2,
            "missing_columns": missing_remedy_in_slot2,
            "required_columns": REQUIRED_REMEDY_COLUMNS,
        },
    }
