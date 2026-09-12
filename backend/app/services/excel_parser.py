"""
Excel File Parser Service
=========================
Handles reading modern (.xlsx via openpyxl) and legacy binary (.xls via xlrd) Excel files.
Located in app/services/excel_parser.py.
"""

import io
from typing import Any
import openpyxl
import pandas as pd


def _parse_read_only_openpyxl(stream_or_path: Any) -> pd.DataFrame | None:
    """
    Lightweight openpyxl SAX streaming parser (read_only=True, data_only=True).
    Reduces memory usage from ~450MB down to ~15MB for large Excel files to prevent Render OOM kills.
    """
    try:
        wb = openpyxl.load_workbook(stream_or_path, read_only=True, data_only=True)
        sheet = wb.active
        if sheet is None:
            return None
        rows_gen = sheet.iter_rows(values_only=True)
        headers = next(rows_gen, None)
        if not headers:
            return None
        data = list(rows_gen)
        wb.close()
        return pd.DataFrame(data, columns=headers)
    except Exception:
        return None


def parse_excel_raw(stream_or_path_or_bytes: Any) -> pd.DataFrame | None:
    """
    Parses Excel (.xlsx or .xls) binary files into a pandas DataFrame using openpyxl or xlrd multi-engine fallbacks.
    
    Args:
        stream_or_path_or_bytes: BytesIO buffer, FileStorage stream, filepath string, or raw bytes.

    Returns:
        pd.DataFrame if successfully parsed, or None if unparseable.
    """
    target: Any
    if hasattr(stream_or_path_or_bytes, "read"):
        content = stream_or_path_or_bytes.read()
        if hasattr(stream_or_path_or_bytes, "seek"):
            stream_or_path_or_bytes.seek(0)
        target = io.BytesIO(content)
    else:
        target = stream_or_path_or_bytes

    # Attempt 1: openpyxl SAX read-only parser
    df = _parse_read_only_openpyxl(target)
    if df is not None and not df.empty:
        return df

    # Attempt 2: openpyxl standard pandas read_excel
    if hasattr(target, "seek"):
        target.seek(0)
    try:
        df = pd.read_excel(target, engine="openpyxl")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    # Attempt 3: xlrd for legacy binary .xls files
    if hasattr(target, "seek"):
        target.seek(0)
    try:
        df = pd.read_excel(target, engine="xlrd")
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    # Attempt 4: Default pandas read_excel auto-engine
    if hasattr(target, "seek"):
        target.seek(0)
    try:
        df = pd.read_excel(target)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    return None


def parse_excel_file(file_input: Any, filename: str = "") -> dict[str, Any]:
    """
    Backward-compatible entry point delegating to central file_parser.parse_file.
    """
    from app.services.file_parser import parse_file
    return parse_file(file_input, filename=filename)


# Re-exports for backward compatibility with existing tests
def __getattr__(name: str) -> Any:
    if name in ("REQUIRED_COLUMNS", "SR_NUMBER_VARIANTS", "OPTIONAL_KPI_MAPPINGS", "normalize_column_name", "validate_and_map_headers", "_sanitize_cell"):
        import app.services.file_parser as fp
        return getattr(fp, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
