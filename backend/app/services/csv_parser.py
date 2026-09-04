"""
CSV Parser Service
==================
Handles reading CSV files with multi-encoding fallback detection (utf-8, latin1, cp1252, iso-8859-1).
Located alongside excel_parser.py in app/services/.
"""

from typing import Any
import pandas as pd


def parse_csv_file(stream_or_path_or_bytes: Any) -> pd.DataFrame | None:
    """
    Parses CSV data into a pandas DataFrame using multi-encoding fallback detection.
    
    Supported Encodings:
    - utf-8 (Standard Unicode)
    - latin1 (ISO-8859-1 / Western European)
    - cp1252 (Windows English / Western European)
    - iso-8859-1
    
    Args:
        stream_or_path_or_bytes: BytesIO buffer, FileStorage, filepath string, or raw bytes.
        
    Returns:
        pd.DataFrame if successfully parsed, or None if unparseable/invalid.
    """
    encodings = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
    for enc in encodings:
        try:
            if hasattr(stream_or_path_or_bytes, "seek"):
                stream_or_path_or_bytes.seek(0)
            df = pd.read_csv(stream_or_path_or_bytes, encoding=enc, low_memory=False)
            if df is not None and len(df.columns) > 0:
                return df
        except Exception:
            continue
    return None
