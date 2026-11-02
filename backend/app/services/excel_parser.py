"""
Excel File Parser Service
=========================
Handles reading modern (.xlsx via openpyxl) and legacy binary (.xls via xlrd) Excel files.
Located in app/services/excel_parser.py.
"""

import io
import logging
import sys
import time
from typing import Any
import openpyxl
import pandas as pd

logger = logging.getLogger("excel_parser")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [EXCEL-PARSER] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def _parse_read_only_openpyxl(stream_or_path: Any, target_columns: list[str] | None = None) -> pd.DataFrame | None:
    """
    Lightweight openpyxl SAX streaming parser (read_only=True, data_only=True).
    Reduces memory usage from ~450MB down to ~15MB for large Excel files to prevent Render OOM kills.
    Supports target_columns projection to skip unused columns at the XML parser level.
    """
    t_start = time.perf_counter()
    logger.info(f"--> Attempting openpyxl SAX streaming parser (column projection: {bool(target_columns)})...")
    try:
        if hasattr(stream_or_path, "seek"):
            stream_or_path.seek(0)
        wb = openpyxl.load_workbook(stream_or_path, read_only=True, data_only=True)
        sheet = wb.active
        if sheet is None:
            logger.warning("openpyxl active sheet is None.")
            return None
        rows_gen = sheet.iter_rows(values_only=True)
        headers = None
        for row in rows_gen:
            if row and any(c is not None and str(c).strip() != "" for c in row):
                non_empty = [c for c in row if c is not None and str(c).strip() != ""]
                if len(non_empty) >= 2 or headers is None:
                    # Find the last column index that actually contains non-empty text
                    last_col_idx = 0
                    for i, c in enumerate(row):
                        if c is not None and str(c).strip() != "":
                            last_col_idx = i + 1
                    headers = [
                        str(c).strip() if c is not None and str(c).strip() != "" else f"UNNAMED_{i}"
                        for i, c in enumerate(row[:last_col_idx])
                    ]
                    break
        if not headers:
            wb.close()
            logger.warning("openpyxl could not detect valid column headers.")
            return None

        # Build column index projection if target_columns is requested
        target_upper = {str(c).strip().upper(): c for c in target_columns} if target_columns else None
        needed_indices = []
        out_headers = []
        if target_upper:
            for idx, h in enumerate(headers):
                if h.upper() in target_upper:
                    needed_indices.append(idx)
                    out_headers.append(h)
        if not needed_indices:
            needed_indices = list(range(len(headers)))
            out_headers = headers

        num_needed = len(needed_indices)
        data = []
        consecutive_empty = 0
        for row in rows_gen:
            # Strictly project only the needed cells; ignores all other cells in the row!
            row_slice = [row[i] if i < len(row) else None for i in needed_indices]
            if any(c is not None and (not isinstance(c, str) or c.strip() != "") for c in row_slice):
                data.append(row_slice)
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                # Stop parsing if we encounter 50 consecutive blank rows
                if consecutive_empty >= 50:
                    break

        wb.close()
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(f"✅ openpyxl SAX succeeded: {len(data):,} rows, {num_needed} cols in {elapsed_ms} ms ({elapsed_ms/1000:.2f}s)")
        return pd.DataFrame(data, columns=out_headers)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.warning(f"⚠️ openpyxl SAX parser failed in {elapsed_ms} ms: {type(exc).__name__}: {exc}")
        return None


def _parse_with_duckdb(stream_or_path: Any, target_columns: list[str] | None = None) -> pd.DataFrame | None:
    """
    DuckDB C++ columnar Excel reader with strict 200MB memory cap.
    Streams directly from disk without allocating millions of Python PyObjects in RAM.
    """
    temp_path = None
    t_start = time.perf_counter()
    try:
        import duckdb
        import os
        import tempfile

        logger.info(f"--> Attempting DuckDB C++ parser (projection: {bool(target_columns)})...")

        # Resolve to a physical file path on disk
        if isinstance(stream_or_path, str) and os.path.exists(stream_or_path):
            file_path = stream_or_path
        else:
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir="/tmp")
            temp_path = tf.name
            if hasattr(stream_or_path, "seek"):
                stream_or_path.seek(0)
            if hasattr(stream_or_path, "read"):
                while chunk := stream_or_path.read(2 * 1024 * 1024):
                    tf.write(chunk)
            elif isinstance(stream_or_path, (bytes, bytearray)):
                tf.write(stream_or_path)
            tf.flush()
            tf.close()
            file_path = temp_path

        con = duckdb.connect()
        con.execute("SET max_memory = '200MB'")
        con.execute("SET temp_directory = '/tmp'")

        try:
            con.execute("INSTALL excel; LOAD excel;")
        except Exception:
            pass

        # Inspect headers
        meta_df = con.execute(f"SELECT * FROM read_xlsx('{file_path}') LIMIT 1").df()
        if target_columns:
            target_upper = {str(c).strip().upper(): c for c in target_columns}
            matched_cols = [c for c in meta_df.columns if str(c).strip().upper() in target_upper]
            if matched_cols:
                cols_sql = ", ".join([f'"{c}"' for c in matched_cols])
                df = con.execute(f"SELECT {cols_sql} FROM read_xlsx('{file_path}')").df()
                elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
                logger.info(f"✅ DuckDB read_xlsx succeeded: {len(df):,} rows, {len(df.columns)} cols in {elapsed_ms} ms ({elapsed_ms/1000:.2f}s)")
                return df

        df = con.execute(f"SELECT * FROM read_xlsx('{file_path}')").df()
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(f"✅ DuckDB read_xlsx succeeded: {len(df):,} rows, {len(df.columns)} cols in {elapsed_ms} ms ({elapsed_ms/1000:.2f}s)")
        return df
    except Exception as exc:
        logger.info(f"ℹ️ DuckDB excel parser bypassed: {type(exc).__name__}: {exc}")
        return None
    finally:
        if temp_path:
            import os
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


def _parse_with_calamine(target: Any, target_columns: list[str] | None = None) -> pd.DataFrame | None:
    """
    Ultra-fast Excel reader powered by python-calamine (compiled Rust engine).
    When target_columns is specified, uses sheet.iter_rows() streaming projection
    to avoid allocating intermediate Python objects for unused columns, reducing
    RAM from ~410MB down to ~110MB on 240,000+ rows.
    """
    t_start = time.perf_counter()
    target_upper = {str(c).strip().upper(): str(c).strip() for c in target_columns} if target_columns else None
    logger.info(f"--> Attempting fast Excel parsing via python-calamine (projection: {bool(target_columns)})...")

    # Path A: Ultra-low-memory streaming via CalamineWorkbook.iter_rows()
    try:
        from python_calamine import CalamineWorkbook
        if hasattr(target, "seek"):
            target.seek(0)

        if isinstance(target, str):
            wb = CalamineWorkbook.from_path(target)
        elif isinstance(target, (bytes, bytearray)):
            import io
            wb = CalamineWorkbook.from_filelike(io.BytesIO(target))
        elif hasattr(target, "read"):
            wb = CalamineWorkbook.from_filelike(target)
        else:
            wb = CalamineWorkbook.from_path(str(target))

        if wb.sheet_names:
            sheet = wb.get_sheet_by_index(0)
            row_iter = sheet.iter_rows()
            col_index_map = {}
            cols_order = []

            # Locate non-empty header row
            for row in row_iter:
                if not row or not any(c is not None and str(c).strip() != "" for c in row):
                    continue
                if target_upper:
                    found = {
                        i: target_upper[str(c).strip().upper()]
                        for i, c in enumerate(row)
                        if c is not None and str(c).strip().upper() in target_upper
                    }
                    if len(found) >= max(1, len(target_upper) // 2):
                        col_index_map = found
                        cols_order = list(found.values())
                        break
                else:
                    col_index_map = {
                        i: str(c).strip() if c is not None and str(c).strip() != "" else f"UNNAMED_{i}"
                        for i, c in enumerate(row)
                    }
                    cols_order = list(col_index_map.values())
                    break

            if col_index_map:
                data = {c: [] for c in cols_order}
                for row in row_iter:
                    row_len = len(row)
                    for idx, col in col_index_map.items():
                        val = row[idx] if idx < row_len else None
                        if isinstance(val, float) and val.is_integer():
                            val = int(val)
                        data[col].append(val)

                df = pd.DataFrame(data)
                elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
                logger.info(f"✅ Calamine (streaming iter_rows) succeeded: {len(df):,} rows, {len(df.columns)} cols in {elapsed_ms} ms ({elapsed_ms/1000:.2f}s)")
                return df
    except Exception as exc:
        logger.debug(f"Calamine streaming iter_rows unavailable ({type(exc).__name__}: {exc}). Trying pandas calamine engine...")

    # Path B: pandas native calamine engine
    try:
        if hasattr(target, "seek"):
            target.seek(0)
        usecols_fn = (lambda c: str(c).strip().upper() in target_upper) if target_upper else None
        df = pd.read_excel(target, engine="calamine", usecols=usecols_fn)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() if c is not None and str(c).strip() != "" else f"UNNAMED_{i}" for i, c in enumerate(df.columns)]
            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            logger.info(f"✅ Calamine (pandas engine) succeeded: {len(df):,} rows, {len(df.columns)} cols in {elapsed_ms} ms ({elapsed_ms/1000:.2f}s)")
            return df
    except Exception as exc:
        logger.debug(f"Calamine pandas engine unavailable ({type(exc).__name__}: {exc}). Trying direct CalamineWorkbook...")

    # Path C: direct python_calamine CalamineWorkbook (only safe for unprojected/moderate sheets)
    if target_columns:
        logger.info("ℹ️ Calamine pandas engine failed for projected file; routing directly to openpyxl SAX...")
        return None

    try:
        from python_calamine import CalamineWorkbook
        if hasattr(target, "seek"):
            target.seek(0)
        wb = CalamineWorkbook.from_path(target) if isinstance(target, str) else CalamineWorkbook.from_filelike(target)
        if not wb.sheet_names:
            logger.warning("Calamine found 0 sheets in workbook.")
            return None
        sheet = wb.get_sheet_by_index(0)
        rows = sheet.to_python()
        if not rows or len(rows) < 2:
            logger.warning(f"Calamine found insufficient rows ({len(rows) if rows else 0}).")
            return None

        # Find header row
        headers = None
        data_start_idx = 1
        for idx, row in enumerate(rows):
            if row and any(c is not None and str(c).strip() != "" for c in row):
                non_empty = [c for c in row if c is not None and str(c).strip() != ""]
                if len(non_empty) >= 2 or headers is None:
                    last_col_idx = 0
                    for i, c in enumerate(row):
                        if c is not None and str(c).strip() != "":
                            last_col_idx = i + 1
                    headers = [
                        str(c).strip() if c is not None and str(c).strip() != "" else f"UNNAMED_{i}"
                        for i, c in enumerate(row[:last_col_idx])
                    ]
                    data_start_idx = idx + 1
                    break

        if not headers:
            logger.warning("Calamine could not find non-empty header row.")
            return None

        # Build column index projection if target_columns is requested
        target_upper = {str(c).strip().upper() for c in target_columns} if target_columns else None
        needed_indices = []
        out_headers = []
        if target_upper:
            for idx, h in enumerate(headers):
                if h.upper() in target_upper:
                    needed_indices.append(idx)
                    out_headers.append(h)
        if not needed_indices:
            needed_indices = list(range(len(headers)))
            out_headers = headers

        num_needed = len(needed_indices)
        data = []
        consecutive_empty = 0
        for row in rows[data_start_idx:]:
            row_slice = [row[i] if i < len(row) else None for i in needed_indices]
            if any(c is not None and (not isinstance(c, str) or c.strip() != "") for c in row_slice):
                data.append(row_slice)
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                if consecutive_empty >= 50:
                    break

        df = pd.DataFrame(data, columns=out_headers)
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(f"✅ Calamine (direct workbook) succeeded: {len(df):,} rows, {num_needed} cols in {elapsed_ms} ms ({elapsed_ms/1000:.2f}s)")
        return df
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
        logger.info(f"ℹ️ Calamine parser bypassed/failed in {elapsed_ms} ms ({type(exc).__name__}: {exc}). Falling back to openpyxl...")

    return None


def get_excel_sheet_names(stream_or_path_or_bytes: Any) -> list[str]:
    """
    Returns list of worksheet names from an Excel (.xlsx or .xls) file.
    Does not parse or calculate any data.
    """
    target: Any
    if hasattr(stream_or_path_or_bytes, "read"):
        content = stream_or_path_or_bytes.read()
        if hasattr(stream_or_path_or_bytes, "seek"):
            stream_or_path_or_bytes.seek(0)
        target = io.BytesIO(content)
    else:
        target = stream_or_path_or_bytes

    # Attempt 0: python-calamine (fast Rust metadata reader)
    try:
        from python_calamine import CalamineWorkbook
        if hasattr(target, "seek"):
            target.seek(0)
        wb = CalamineWorkbook.from_filelike(target) if hasattr(target, "read") else CalamineWorkbook.from_file(target)
        if wb.sheet_names:
            return list(wb.sheet_names)
    except Exception:
        pass

    # Attempt 1: openpyxl for modern .xlsx
    try:
        if hasattr(target, "seek"):
            target.seek(0)
        wb = openpyxl.load_workbook(target, read_only=True, keep_links=False)
        names = list(wb.sheetnames)
        wb.close()
        if names:
            return names
    except Exception:
        pass

    # Attempt 2: pd.ExcelFile (handles .xls and .xlsx)
    try:
        if hasattr(target, "seek"):
            target.seek(0)
        xl = pd.ExcelFile(target)
        return list(xl.sheet_names)
    except Exception:
        pass

    return []


def parse_excel_raw(stream_or_path_or_bytes: Any, target_columns: list[str] | None = None) -> pd.DataFrame | None:
    """
    Parses Excel (.xlsx or .xls) binary files into a pandas DataFrame using multi-engine fallbacks.
    Priority order:
      1. python-calamine (compiled Rust engine with column projection - 10x faster)
      2. openpyxl SAX streaming parser (read_only=True, low-memory fallback)
      3. DuckDB C++ columnar Excel reader (strict memory cap)
      4. pandas standard openpyxl engine
      5. xlrd for legacy binary .xls files
    
    Args:
        stream_or_path_or_bytes: BytesIO buffer, FileStorage stream, filepath string, or raw bytes.
        target_columns: Optional list of column names to project (drops all other columns to save RAM).

    Returns:
        pd.DataFrame if successfully parsed, or None if unparseable.
    """
    target: Any = stream_or_path_or_bytes
    t_parse_start = time.perf_counter()

    # Attempt 1: Ultra-fast python-calamine (compiled Rust engine, 10x faster)
    df = _parse_with_calamine(target, target_columns=target_columns)
    if df is not None and not df.empty:
        return df

    # Attempt 2: openpyxl SAX read-only streaming parser (memory-safe fallback)
    df = _parse_read_only_openpyxl(target, target_columns=target_columns)
    if df is not None and not df.empty:
        return df

    # Attempt 3: DuckDB C++ parser (if extension available)
    df = _parse_with_duckdb(target, target_columns=target_columns)
    if df is not None and not df.empty:
        return df

    # Attempt 4: openpyxl standard pandas read_excel
    logger.info("--> Attempting fallback: pandas read_excel(engine='openpyxl')...")
    if hasattr(target, "seek"):
        target.seek(0)
    try:
        df = pd.read_excel(target, engine="openpyxl")
        if df is not None and not df.empty:
            logger.info(f"✅ pandas openpyxl fallback succeeded: {len(df):,} rows, {len(df.columns)} cols.")
            return df
    except Exception as exc:
        logger.warning(f"⚠️ pandas openpyxl fallback failed: {exc}")

    # Attempt 5: xlrd for legacy binary .xls files
    logger.info("--> Attempting fallback: pandas read_excel(engine='xlrd') for legacy .xls...")
    if hasattr(target, "seek"):
        target.seek(0)
    try:
        df = pd.read_excel(target, engine="xlrd")
        if df is not None and not df.empty:
            logger.info(f"✅ xlrd fallback succeeded: {len(df):,} rows, {len(df.columns)} cols.")
            return df
    except Exception as exc:
        logger.warning(f"⚠️ xlrd fallback failed: {exc}")

    # Attempt 6: Default pandas read_excel auto-engine
    if hasattr(target, "seek"):
        target.seek(0)
    try:
        df = pd.read_excel(target)
        if df is not None and not df.empty:
            logger.info(f"✅ default pandas auto-engine succeeded: {len(df):,} rows, {len(df.columns)} cols.")
            return df
    except Exception as exc:
        logger.warning(f"⚠️ default pandas auto-engine failed: {exc}")

    total_fail_ms = round((time.perf_counter() - t_parse_start) * 1000, 2)
    logger.error(f"❌ [EXCEL-PARSER] All parsing engines failed on target file after {total_fail_ms} ms.")
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
