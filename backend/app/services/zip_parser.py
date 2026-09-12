"""
ZIP Archive Parser Service
==========================
Handles extracting and reading spreadsheets (.csv, .xlsx, .xls) from .zip archives.
Concatenates dataframes from all valid internal files into a single unified pandas DataFrame.
Located in app/services/ zip_parser.py.
"""

import io
import os
from typing import Any
import zipfile
import pandas as pd

from app.services.csv_parser import parse_csv_file
from app.services.excel_parser import parse_excel_raw


def _parse_member_file(file_bytes: bytes, filename: str) -> pd.DataFrame | None:
    """Helper to parse raw bytes of an extracted zip file based on its extension/content."""
    ext = os.path.splitext(filename)[1].lower()
    bytes_io = io.BytesIO(file_bytes)

    if ext == ".csv":
        return parse_csv_file(bytes_io)

    if ext in (".xlsx", ".xls"):
        df = parse_excel_raw(bytes_io)
        if df is not None and not df.empty:
            return df

    # Fallback: attempt CSV then Excel parsing regardless of extension
    df = parse_csv_file(bytes_io)
    if df is not None and not df.empty:
        return df

    bytes_io.seek(0)
    return parse_excel_raw(bytes_io)


def parse_zip_file(stream_or_path_or_bytes: Any) -> pd.DataFrame | None:
    """
    Parses a ZIP archive containing spreadsheet files (.csv, .xlsx, .xls).
    
    Reads all non-hidden CSV and Excel files contained within the ZIP (including nested subdirectories),
    parses each into a DataFrame, and concatenates them into a single pandas DataFrame.

    Args:
        stream_or_path_or_bytes: BytesIO buffer, FileStorage, filepath string, or raw bytes.

    Returns:
        pd.DataFrame if successfully parsed at least one file, or None if unparseable/empty.
    """
    try:
        # Prepare ZipFile target
        if isinstance(stream_or_path_or_bytes, bytes):
            zip_target: Any = io.BytesIO(stream_or_path_or_bytes)
        elif hasattr(stream_or_path_or_bytes, "read"):
            content = stream_or_path_or_bytes.read()
            if hasattr(stream_or_path_or_bytes, "seek"):
                stream_or_path_or_bytes.seek(0)
            zip_target = io.BytesIO(content)
        else:
            zip_target = stream_or_path_or_bytes

        with zipfile.ZipFile(zip_target, "r") as zf:
            dfs: list[pd.DataFrame] = []
            for member_name in zf.namelist():
                # Skip directories and OS metadata files (e.g. __MACOSX, .DS_Store)
                if member_name.endswith("/") or member_name.endswith("\\"):
                    continue
                basename = os.path.basename(member_name)
                if basename.startswith(".") or "__MACOSX" in member_name:
                    continue

                ext = os.path.splitext(basename)[1].lower()
                if ext in (".csv", ".xlsx", ".xls", ".txt"):
                    try:
                        file_bytes = zf.read(member_name)
                        df = _parse_member_file(file_bytes, basename)
                        if df is not None and not df.empty and len(df.columns) > 0:
                            dfs.append(df)
                    except Exception:
                        continue

            if dfs:
                if len(dfs) == 1:
                    return dfs[0]
                return pd.concat(dfs, ignore_index=True)

    except Exception:
        return None

    return None
