"""
Unit tests for Remedy File Reader (Phase 1)
"""

import io
import pandas as pd
import pytest

from app.services.nstt.remedy_reader import parse_remedy_file, validate_remedy_headers


def test_validate_remedy_headers_valid():
    headers = [
        "INCIDENT_NUMBER",
        "ASSIGNED_SUPPORT_COMPANY",
        "UP_TIME",
        "Submit Date",
        "INCIDENT_IMPACT",
        "DESCRIPTION",
        "EXTRA_FIELD",
    ]
    col_map, missing = validate_remedy_headers(headers)
    assert len(missing) == 0
    assert col_map["INCIDENT_NUMBER"] == "INCIDENT_NUMBER"


def test_validate_remedy_headers_with_variations():
    headers = [
        "Incident ID",
        "Support Company",
        "Circuit Uptime",
        "Submitted Date",
        "Impact",
        "Details",
    ]
    col_map, missing = validate_remedy_headers(headers)
    assert len(missing) == 0


def test_validate_remedy_headers_missing():
    headers = ["INCIDENT_NUMBER", "DESCRIPTION"]
    col_map, missing = validate_remedy_headers(headers)
    assert len(missing) > 0
    assert "UP_TIME" in missing
    assert "Submit Date" in missing


def test_parse_remedy_csv_success():
    csv_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,INCIDENT_IMPACT,DESCRIPTION,EXTRA_REMEDY_COL\n"
        "INC1001,ANG Infotech,2026-09-01 12:00:00,2026-09-01 09:30:00,0,Ring Failure reported,RemedyExtraVal\n"
        "INC1002,Tata Comm,2026-09-01 14:00:00,2026-09-01 10:15:00,1,Normal Maintenance,RemedyExtraVal2\n"
    )
    bio = io.BytesIO(csv_content.encode("utf-8"))
    res = parse_remedy_file(bio, filename="remedy_test.csv")

    assert res["success"] is True
    assert res["row_count"] == 2
    assert res["df"].iloc[0]["INCIDENT_NUMBER"] == "INC1001"
    assert res["df"].iloc[0]["ASSIGNED_SUPPORT_COMPANY"] == "ANG Infotech"


def test_parse_remedy_missing_column_error():
    csv_content = "INCIDENT_NUMBER,DESCRIPTION\nINC1001,Some description\n"
    bio = io.BytesIO(csv_content.encode("utf-8"))
    res = parse_remedy_file(bio, filename="remedy_bad.csv")

    assert res["success"] is False
    assert "missing required column" in res["error"].lower()
    assert len(res["missing_columns"]) > 0
