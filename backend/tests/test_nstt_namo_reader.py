"""
Unit tests for Namo File Reader (Phase 1)
"""

import io
import pandas as pd
import pytest

from app.services.nstt.namo_reader import parse_namo_file, validate_namo_headers


def test_validate_namo_headers_valid():
    headers = [
        "INCIDENTID",
        "ATTRIBUTEDTO",
        "SRCREATIONTIME",
        "FACTORY",
        "AUTO_ALLOCATION",
        "AUTOMATION_UPDATE_NSTT_NUMBER",
        "AUTOMATION_RCA_CONCLUSION_TEXT",
        "EXTRA_FIELD_1",
    ]
    col_map, missing = validate_namo_headers(headers)
    assert len(missing) == 0
    assert col_map["INCIDENTID"] == "INCIDENTID"
    assert "EXTRA_FIELD_1" not in col_map


def test_validate_namo_headers_with_variations():
    headers = [
        "incident_id",
        "attributed to",
        "SR Creation Time",
        "Factory Name",
        "auto allocation",
        "Automation Update Nstt Number",
        "RCA Conclusion Text",
    ]
    col_map, missing = validate_namo_headers(headers)
    assert len(missing) == 0


def test_validate_namo_headers_missing():
    headers = ["INCIDENTID", "FACTORY"]
    col_map, missing = validate_namo_headers(headers)
    assert len(missing) > 0
    assert "ATTRIBUTEDTO" in missing
    assert "SRCREATIONTIME" in missing


def test_parse_namo_csv_success():
    csv_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT,CUSTOM_EXTRA\n"
        "INC1001,TXN,2026-09-01 10:00:00,IM,yes,INC1001,FLT Observations for Unstitched LSI,CustomValue1\n"
        "INC1002,TNL,2026-09-01 11:00:00,Non IM,no,,No Issue,CustomValue2\n"
    )
    bio = io.BytesIO(csv_content.encode("utf-8"))
    res = parse_namo_file(bio, filename="namo_test.csv")

    assert res["success"] is True
    assert res["row_count"] == 2
    assert "CUSTOM_EXTRA" in res["columns"]
    assert res["df"].iloc[0]["INCIDENTID"] == "INC1001"
    assert res["df"].iloc[0]["CUSTOM_EXTRA"] == "CustomValue1"


def test_parse_namo_missing_column_error():
    csv_content = "INCIDENTID,FACTORY\nINC1001,IM\n"
    bio = io.BytesIO(csv_content.encode("utf-8"))
    res = parse_namo_file(bio, filename="namo_bad.csv")

    assert res["success"] is False
    assert "missing required column" in res["error"].lower()
    assert len(res["missing_columns"]) > 0
