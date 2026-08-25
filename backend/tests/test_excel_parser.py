import io
import os
import sys
from datetime import datetime
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.excel_parser import (
    REQUIRED_COLUMNS,
    normalize_column_name,
    parse_excel_file,
    validate_and_map_headers,
)


def create_sample_excel_bytes(data_dict: dict[str, list]) -> io.BytesIO:
    df = pd.DataFrame(data_dict)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


def test_normalize_column_name():
    assert normalize_column_name(" SRCREATIONTIME ") == "SRCREATIONTIME"
    assert normalize_column_name("automation_end_time") == "AUTOMATION_END_TIME"
    assert normalize_column_name("Roster Allocation Time") == "ROSTER_ALLOCATION_TIME"
    assert normalize_column_name("First_Acknowledgement_Time ") == "FIRST_ACKNOWLEDGEMENT_TIME"


def test_validate_and_map_headers_all_present():
    headers = [
        "srcreationtime",
        "AUTOMATION END TIME",
        "roster_allocation_time",
        "FIRST_ACKNOWLEDGEMENT_TIME",
        "ResolvedTime",
        "CreationTime",
        "Circuit_Uptime",
        "EXTRA_UNNEEDED_COLUMN",
    ]
    col_map, missing = validate_and_map_headers(headers)
    assert missing == []
    assert len(col_map) == 7
    assert col_map["srcreationtime"] == "SRCREATIONTIME"
    assert col_map["AUTOMATION END TIME"] == "AUTOMATION_END_TIME"


def test_validate_and_map_headers_creationtime_fallback():
    headers = [
        "SRCREATIONTIME",
        "AUTOMATION_END_TIME",
        "ROSTER_ALLOCATION_TIME",
        "FIRST_ACKNOWLEDGEMENT_TIME",
        "RESOLVEDTIME",
        "CIRCUIT_UPTIME",
        # Notice CREATIONTIME is absent, but SRCREATIONTIME is present
    ]
    col_map, missing = validate_and_map_headers(headers)
    assert missing == []


def test_validate_and_map_headers_missing_column():
    headers = [
        "SRCREATIONTIME",
        "AUTOMATION_END_TIME",
        "ROSTER_ALLOCATION_TIME",
        # Missing FIRST_ACKNOWLEDGEMENT_TIME, RESOLVEDTIME, CREATIONTIME, CIRCUIT_UPTIME
    ]
    col_map, missing = validate_and_map_headers(headers)
    assert len(missing) == 3
    assert "FIRST_ACKNOWLEDGEMENT_TIME" in missing
    assert "RESOLVEDTIME" in missing
    assert "CIRCUIT_UPTIME" in missing


def test_parse_excel_file_success():
    sample_data = {
        "SRCREATIONTIME": ["2026-08-21 08:00:00", "2026-08-22 10:00:00"],
        "Automation_End_Time": ["2026-08-21 14:00:00", "2026-08-22 16:00:00"],
        "ROSTER ALLOCATION TIME": ["2026-08-21 09:00:00", "2026-08-22 11:00:00"],
        "FIRST_ACKNOWLEDGEMENT_TIME": ["2026-08-21 09:30:00", "2026-08-22 11:30:00"],
        "RESOLVEDTIME": ["2026-08-22 12:00:00", "2026-08-23 12:00:00"],
        "CREATIONTIME": ["2026-08-20 10:00:00", "2026-08-21 10:00:00"],
        "CIRCUIT_UPTIME": ["2026-08-22 12:00:00", "2026-08-23 12:00:00"],
        "EXTRA_COL": ["foo", "bar"],
    }
    excel_bytes = create_sample_excel_bytes(sample_data)

    result = parse_excel_file(excel_bytes)
    assert result["success"] is True
    assert result["row_count"] == 2
    rows = result["rows"]
    assert len(rows) == 2
    assert "SRCREATIONTIME" in rows[0]
    assert "AUTOMATION_END_TIME" in rows[0]
    assert "ROSTER_ALLOCATION_TIME" in rows[0]


def test_parse_excel_file_missing_columns_error():
    sample_data = {
        "SRCREATIONTIME": ["2026-08-21 08:00:00"],
        "AUTOMATION_END_TIME": ["2026-08-21 14:00:00"],
        # Missing other required columns
    }
    excel_bytes = create_sample_excel_bytes(sample_data)

    result = parse_excel_file(excel_bytes)
    assert result["success"] is False
    assert "Missing required Excel columns" in result["error"]
    assert len(result["missing_columns"]) == 4


def test_parse_excel_file_invalid_bytes():
    invalid_bytes = io.BytesIO(b"not an excel file content at all")
    result = parse_excel_file(invalid_bytes)
    assert result["success"] is False
    assert "Failed to read Excel file" in result["error"]
