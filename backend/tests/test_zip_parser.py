import io
import zipfile
import pandas as pd
import pytest
from app.services.zip_parser import parse_zip_file


def create_sample_zip(files_dict: dict[str, str | bytes]) -> io.BytesIO:
    """Helper to construct an in-memory zip file from filename -> content dict."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files_dict.items():
            if isinstance(content, str):
                zf.writestr(filename, content.encode("utf-8"))
            else:
                zf.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer


def test_parse_zip_file_single_csv():
    csv_data = "SRNUMBER,SRCREATIONTIME\nSR1001,2026-08-01 10:00:00\nSR1002,2026-08-02 11:00:00\n"
    zip_buf = create_sample_zip({"data.csv": csv_data})
    
    df = parse_zip_file(zip_buf)
    assert df is not None
    assert len(df) == 2
    assert "SRNUMBER" in df.columns
    assert list(df["SRNUMBER"]) == ["SR1001", "SR1002"]


def test_parse_zip_file_multiple_csvs():
    csv1 = "SRNUMBER,SRCREATIONTIME\nSR1001,2026-08-01 10:00:00\n"
    csv2 = "SRNUMBER,SRCREATIONTIME\nSR1002,2026-08-02 11:00:00\n"
    zip_buf = create_sample_zip({"data1.csv": csv1, "data2.csv": csv2})
    
    df = parse_zip_file(zip_buf)
    assert df is not None
    assert len(df) == 2
    assert set(df["SRNUMBER"]) == {"SR1001", "SR1002"}


def test_parse_zip_file_ignores_macosx_and_hidden_files():
    csv_data = "SRNUMBER,SRCREATIONTIME\nSR1001,2026-08-01 10:00:00\n"
    zip_buf = create_sample_zip({
        "__MACOSX/._data.csv": "junk",
        ".DS_Store": "junk",
        "valid_data.csv": csv_data
    })
    
    df = parse_zip_file(zip_buf)
    assert df is not None
    assert len(df) == 1
    assert df["SRNUMBER"].iloc[0] == "SR1001"


def test_parse_zip_file_invalid_zip():
    invalid_buf = io.BytesIO(b"not a zip file content")
    df = parse_zip_file(invalid_buf)
    assert df is None
