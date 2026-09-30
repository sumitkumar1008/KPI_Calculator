"""
Unit tests for Duplicate Checker (Phase 1)
"""

import pandas as pd
import pytest

from app.services.nstt.duplicate_checker import check_duplicates


def test_check_duplicates_with_duplicates():
    df = pd.DataFrame({
        "INCIDENTID": ["INC001", "INC002", "INC001", "INC003", "INC002", "INC004"],
        "VAL": [1, 2, 3, 4, 5, 6],
    })

    res = check_duplicates(df, id_col="INCIDENTID")
    res_df = res["df"]

    assert res["total_records"] == 6
    assert res["unique_incident_ids"] == 4
    assert res["duplicate_records_count"] == 4  # 2 instances of INC001 + 2 of INC002
    assert "INC001" in res["duplicate_incident_ids"]
    assert "INC002" in res["duplicate_incident_ids"]
    assert "INC003" not in res["duplicate_incident_ids"]

    # Ensure NO rows were dropped
    assert len(res_df) == 6

    # Verify flags
    flags = res_df["is_potential_duplicate"].tolist()
    assert flags == [True, True, True, False, True, False]


def test_check_duplicates_no_duplicates():
    df = pd.DataFrame({
        "INCIDENTID": ["INC001", "INC002", "INC003"],
    })

    res = check_duplicates(df)
    assert res["duplicate_records_count"] == 0
    assert len(res["duplicate_incident_ids"]) == 0
    assert all(res["df"]["is_potential_duplicate"] == False)
