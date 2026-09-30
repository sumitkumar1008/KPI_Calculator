"""
Unit tests for VLOOKUP / Join Service (Phase 1)
"""

import pandas as pd
import pytest

from app.services.nstt.vlookup import perform_vlookup


def test_perform_vlookup_success():
    namo_data = {
        "INCIDENTID": ["INC001", "INC002", "INC003"],
        "ATTRIBUTEDTO": ["TXN", "TNL", "TXN_Infra"],
        "SRCREATIONTIME": ["2026-09-01 10:00:00", "2026-09-01 11:00:00", "2026-09-01 12:00:00"],
        "FACTORY": ["IM", "Non IM", "IM"],
        "AUTO_ALLOCATION": ["yes", "no", "yes"],
        "AUTOMATION_UPDATE_NSTT_NUMBER": ["INC001", "", "INC003"],
        "AUTOMATION_RCA_CONCLUSION_TEXT": ["Text1", "Text2", "Text3"],
        "CUSTOM_NAMO_COL": ["Alpha", "Beta", "Gamma"],
    }
    remedy_data = {
        "INCIDENT_NUMBER": ["INC001", "INC002"],
        "ASSIGNED_SUPPORT_COMPANY": ["ANG Co", "Other Co"],
        "UP_TIME": ["2026-09-01 15:00:00", "2026-09-01 16:00:00"],
        "Submit Date": ["2026-09-01 09:00:00", "2026-09-01 09:30:00"],
        "INCIDENT_IMPACT": [0, 1],
        "DESCRIPTION": ["Ring failure detected", "Normal breakdown"],
        "EXTRA_REMEDY_COL_SHOULD_BE_IGNORED": ["Ignored1", "Ignored2"],
    }

    namo_df = pd.DataFrame(namo_data)
    remedy_df = pd.DataFrame(remedy_data)

    res = perform_vlookup(namo_df, remedy_df)
    df = res["df"]

    assert res["total_namo_rows"] == 3
    assert res["matched_count"] == 2
    assert res["unmatched_count"] == 1
    assert "INC003" in res["unmatched_ids"]

    # Check that ALL Namo columns are preserved
    assert "CUSTOM_NAMO_COL" in df.columns
    assert df.loc[df["INCIDENTID"] == "INC001", "CUSTOM_NAMO_COL"].values[0] == "Alpha"

    # Check that 5 Remedy columns are appended
    assert "ASSIGNED_SUPPORT_COMPANY" in df.columns
    assert "UP_TIME" in df.columns
    assert "Submit Date" in df.columns
    assert "INCIDENT_IMPACT" in df.columns
    assert "DESCRIPTION" in df.columns

    # Check that non-required Remedy columns are NOT appended
    assert "EXTRA_REMEDY_COL_SHOULD_BE_IGNORED" not in df.columns

    # Check is_matched flags
    assert df.loc[df["INCIDENTID"] == "INC001", "is_matched"].values[0] == True
    assert df.loc[df["INCIDENTID"] == "INC003", "is_matched"].values[0] == False


def test_perform_vlookup_whitespace_handling():
    namo_df = pd.DataFrame({
        "INCIDENTID": [" INC001 "],
        "ATTRIBUTEDTO": ["TXN"],
    })
    remedy_df = pd.DataFrame({
        "INCIDENT_NUMBER": ["inc001"],
        "ASSIGNED_SUPPORT_COMPANY": ["Company A"],
        "UP_TIME": ["2026-09-01"],
        "Submit Date": ["2026-09-01"],
        "INCIDENT_IMPACT": ["SA"],
        "DESCRIPTION": ["Desc"],
    })

    res = perform_vlookup(namo_df, remedy_df)
    assert res["matched_count"] == 1
    assert res["unmatched_count"] == 0
