"""
ZIP Archive Parser Service
==========================
Handles extracting and reading spreadsheets (.csv, .xlsx, .xls) from .zip archives.
Concatenates dataframes from all valid internal files into a single unified pandas DataFrame.
Located in app/services/ zip_parser.py.
"""

import io
import os
import shutil
import tempfile
from typing import Any
import zipfile
import pandas as pd

from app.services.csv_parser import parse_csv_file
from app.services.excel_parser import parse_excel_raw


def _parse_member_stream(
    src_stream: Any,
    filename: str,
    target_columns: list[str] | None = None,
    prefer_calamine: bool = True,
) -> pd.DataFrame | None:
    """
    Streams an extracted ZIP member file directly to a temporary file on disk in 64KB chunks,
    completely bypassing holding 80MB+ raw byte buffers in RAM.
    """
    ext = os.path.splitext(filename)[1].lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            shutil.copyfileobj(src_stream, tmp, length=64 * 1024)

        if ext == ".csv":
            return parse_csv_file(tmp_path, target_columns=target_columns)

        if ext in (".xlsx", ".xls"):
            df = parse_excel_raw(tmp_path, target_columns=target_columns, prefer_calamine=prefer_calamine)
            if df is not None and not df.empty:
                return df

        # Fallback: attempt CSV then Excel parsing regardless of extension
        df = parse_csv_file(tmp_path, target_columns=target_columns)
        if df is not None and not df.empty:
            return df

        return parse_excel_raw(tmp_path, target_columns=target_columns, prefer_calamine=prefer_calamine)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def parse_zip_file(
    stream_or_path_or_bytes: Any,
    target_columns: list[str] | None = None,
    prefer_calamine: bool = True,
) -> pd.DataFrame | None:
    """
    Parses a ZIP archive containing spreadsheet files (.csv, .xlsx, .xls).
    Streams member files directly to disk to prevent RAM spikes on memory-constrained servers (Render 512MB).
    Supports target_columns projection and Calamine Rust parsing.

    Args:
        stream_or_path_or_bytes: BytesIO buffer, FileStorage, filepath string, or raw bytes.
        target_columns: Optional list of column names to project (drops all other columns to save RAM).
        prefer_calamine: Whether to prioritize python-calamine compiled Rust engine.

    Returns:
        pd.DataFrame if successfully parsed at least one file, or None if unparseable/empty.
    """
    temp_zip_path = None
    try:
        # Prepare ZipFile target without duplicating large buffers in RAM
        if isinstance(stream_or_path_or_bytes, bytes):
            zip_target: Any = io.BytesIO(stream_or_path_or_bytes)
        elif hasattr(stream_or_path_or_bytes, "read"):
            # If large stream, write directly to temporary disk file to save RAM
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_z:
                temp_zip_path = tmp_z.name
                if hasattr(stream_or_path_or_bytes, "seek"):
                    stream_or_path_or_bytes.seek(0)
                shutil.copyfileobj(stream_or_path_or_bytes, tmp_z, length=64 * 1024)
            zip_target = temp_zip_path
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
                        with zf.open(member_name) as member_stream:
                            df = _parse_member_stream(
                                member_stream,
                                basename,
                                target_columns=target_columns,
                                prefer_calamine=prefer_calamine,
                            )
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
    finally:
        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except Exception:
                pass

    return None
