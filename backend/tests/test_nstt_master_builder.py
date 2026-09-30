"""
Unit tests for Master Response Builder (Phase 1)
"""

import datetime
import numpy as np
import pandas as pd
import pytest

from app.services.nstt.master_builder import build_master_response, _sanitize_nstt_cell


def test_sanitize_nstt_cell():
    assert _sanitize_nstt_cell(None) is None
    assert _sanitize_nstt_cell(np.nan) is None
    assert _sanitize_nstt_cell(pd.NaT) is None
    assert _sanitize_nstt_cell(123) == 123
    assert _sanitize_nstt_cell(12.5) == 12.5
    assert _sanitize_nstt_cell(True) is True
    assert _sanitize_nstt_cell("Test") == "Test"

    dt = datetime.datetime(2026, 9, 1, 12, 0, 0)
    assert _sanitize_nstt_cell(dt) == "2026-09-01T12:00:00"


def test_build_master_response():
    df = pd.DataFrame({
        "INCIDENTID": ["INC001", "INC002"],
        "ATTRIBUTEDTO": ["TXN", "TNL"],
        "SRCREATIONTIME": [pd.Timestamp("2026-09-01 10:00:00"), None],
        "FACTORY": ["IM", "Non IM"],
        "AUTO_ALLOCATION": ["yes", "no"],
        "AUTOMATION_UPDATE_NSTT_NUMBER": ["INC001", ""],
        "AUTOMATION_RCA_CONCLUSION_TEXT": ["Text1", None],
        "ASSIGNED_SUPPORT_COMPANY": ["ANG", None],
        "UP_TIME": [pd.Timestamp("2026-09-01 12:00:00"), None],
        "Submit Date": [pd.Timestamp("2026-09-01 09:00:00"), None],
        "INCIDENT_IMPACT": ["SA", "NSA"],
        "DESCRIPTION": ["Desc1", "Desc2"],
        "is_matched": [True, False],
        "is_potential_duplicate": [False, True],
        "EXTRA_CUSTOM_FIELD": [100, np.nan],
    })

    master = build_master_response(df)

    assert master["total_records"] == 2
    assert len(master["records"]) == 2
    assert "EXTRA_CUSTOM_FIELD" in master["columns"]

    rec1 = master["records"][0]
    assert rec1["INCIDENTID"] == "INC001"
    assert rec1["is_matched"] is True
    assert rec1["is_potential_duplicate"] is False
    assert rec1["EXTRA_CUSTOM_FIELD"] == 100
    assert rec1["SRCREATIONTIME"] == "2026-09-01T10:00:00"

    rec2 = master["records"][1]
    assert rec2["INCIDENTID"] == "INC002"
    assert rec2["is_matched"] is False
    assert rec2["is_potential_duplicate"] is True
    assert rec2["EXTRA_CUSTOM_FIELD"] is None
    assert rec2["SRCREATIONTIME"] is None
