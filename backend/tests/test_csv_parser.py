import io
import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.csv_parser import parse_csv_file


def test_parse_csv_file_valid_utf8():
    csv_data = "SRNUMBER,VALUE\nSR-001,100\nSR-002,200\n"
    buf = io.BytesIO(csv_data.encode("utf-8"))
    df = parse_csv_file(buf)
    assert df is not None
    assert len(df) == 2
    assert list(df.columns) == ["SRNUMBER", "VALUE"]
    assert df.iloc[0]["SRNUMBER"] == "SR-001"


def test_parse_csv_file_latin1_encoding():
    csv_data = "SRNUMBER,DESCRIPTION\nSR-001,Café Alert\n"
    buf = io.BytesIO(csv_data.encode("latin1"))
    df = parse_csv_file(buf)
    assert df is not None
    assert len(df) == 1
    assert df.iloc[0]["SRNUMBER"] == "SR-001"


def test_parse_csv_file_invalid_input():
    buf = io.BytesIO(b"")
    df = parse_csv_file(buf)
    assert df is None
