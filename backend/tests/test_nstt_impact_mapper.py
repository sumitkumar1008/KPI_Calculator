"""
Unit tests for INCIDENT_IMPACT Mapper (Phase 1)
"""

import pandas as pd
import pytest

from app.services.nstt.impact_mapper import map_incident_impact, map_single_impact


def test_map_single_impact():
    assert map_single_impact(0) == "SA"
    assert map_single_impact("0") == "SA"
    assert map_single_impact(0.0) == "SA"
    assert map_single_impact("SA") == "SA"
    assert map_single_impact("sa") == "SA"

    assert map_single_impact(1) == "NSA"
    assert map_single_impact("1") == "NSA"
    assert map_single_impact(1.0) == "NSA"
    assert map_single_impact("NSA") == "NSA"
    assert map_single_impact("nsa") == "NSA"

    assert map_single_impact(None) is None
    assert map_single_impact("") is None
    assert map_single_impact("2") is None
    assert map_single_impact("OTHER") is None


def test_map_incident_impact_dataframe():
    df = pd.DataFrame({
        "INCIDENTID": ["INC1", "INC2", "INC3", "INC4", "INC5"],
        "INCIDENT_IMPACT": [0, "1", "SA", 99, None],
    })
    res_df = map_incident_impact(df)
    results = [x if pd.notna(x) else None for x in res_df["INCIDENT_IMPACT"]]
    assert results == ["SA", "NSA", "SA", None, None]
