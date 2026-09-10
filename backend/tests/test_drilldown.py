"""
Tests for Drilldown Service and Endpoint
=========================================
"""

import pytest
from app.services.drilldown_service import (
    filter_rows_by_month,
    filter_rows_by_week,
    get_table_drilldown,
)


@pytest.fixture
def sample_rows():
    return [
        {
            "SRNUMBER": "SR1001",
            "SRCREATIONTIME": "2026-08-02T10:00:00",
            "AUTOMATION_RUN": "Y",
            "AUTOMATION_RCA_CONCLUSION": "Y",
            "MTTI": "00:05:00",
            "MTTA": "00:10:00",
            "MTTAck": "00:02:00",
            "MTTR": "01:00:00",
            "MTTr": "00:50:00",
            "MTTI_seconds": 300,
            "MTTA_seconds": 600,
            "MTTAck_seconds": 120,
            "MTTR_seconds": 3600,
            "MTTr_seconds": 3000,
        },
        {
            "SRNUMBER": "SR1002",
            "SRCREATIONTIME": "2026-08-05T14:30:00",
            "AUTOMATION_RUN": "N",
            "AUTOMATION_RCA_CONCLUSION": "Y",
            "MTTI": "00:10:00",
            "MTTA": "00:15:00",
            "MTTAck": "00:05:00",
            "MTTR": "02:00:00",
            "MTTr": "01:30:00",
            "MTTI_seconds": 600,
            "MTTA_seconds": 900,
            "MTTAck_seconds": 300,
            "MTTR_seconds": 7200,
            "MTTr_seconds": 5400,
        },
        {
            "SRNUMBER": "SR1003",
            "SRCREATIONTIME": "2026-08-10T09:00:00",  # Week 2
            "AUTOMATION_RUN": "Y",
            "AUTOMATION_RCA_CONCLUSION": "N",
            "MTTI": "00:08:00",
            "MTTA": "00:12:00",
            "MTTAck": "00:03:00",
            "MTTR": "01:30:00",
            "MTTr": "01:00:00",
            "MTTI_seconds": 480,
            "MTTA_seconds": 720,
            "MTTAck_seconds": 180,
            "MTTR_seconds": 5400,
            "MTTr_seconds": 3600,
        },
        {
            "SRNUMBER": "SR2001",
            "SRCREATIONTIME": "2026-09-01T10:00:00",  # September record
            "AUTOMATION_RUN": "Y",
            "AUTOMATION_RCA_CONCLUSION": "Y",
            "MTTI": "00:04:00",
            "MTTA": "00:08:00",
            "MTTAck": "00:01:00",
            "MTTR": "00:45:00",
            "MTTr": "00:30:00",
            "MTTI_seconds": 240,
            "MTTA_seconds": 480,
            "MTTAck_seconds": 60,
            "MTTR_seconds": 2700,
            "MTTr_seconds": 1800,
        },
    ]


def test_filter_rows_by_month(sample_rows):
    aug_rows = filter_rows_by_month(sample_rows, "2026-08")
    assert len(aug_rows) == 3
    assert all(r["SRNUMBER"].startswith("SR10") for r in aug_rows)


def test_filter_rows_by_week(sample_rows):
    week1_rows = filter_rows_by_week(sample_rows, "2026-08", 1)
    assert len(week1_rows) == 2
    assert week1_rows[0]["SRNUMBER"] == "SR1001"
    assert week1_rows[1]["SRNUMBER"] == "SR1002"

    week2_rows = filter_rows_by_week(sample_rows, "2026-08", 2)
    assert len(week2_rows) == 1
    assert week2_rows[0]["SRNUMBER"] == "SR1003"


def test_get_table_drilldown_level_1_weekly(sample_rows):
    result = get_table_drilldown(sample_rows, table_type="avg", month="2026-08")
    assert result["level"] == "weekly"
    assert len(result["summary"]) == 2  # Week 1 and Week 2 exist in sample
    assert result["summary"][0]["period_label"] == "August 2026 - Week 1"


def test_get_table_drilldown_level_2_daily(sample_rows):
    result = get_table_drilldown(sample_rows, table_type="avg", month="2026-08", week=1)
    assert result["level"] == "daily"
    assert len(result["summary"]) == 2  # Aug 2 and Aug 5
    assert result["summary"][0]["period"] == "2026-08-02"
    assert result["summary"][1]["period"] == "2026-08-05"


def test_drilldown_api_endpoint(client, sample_rows):
    payload = {
        "rows": sample_rows,
        "table_type": "automation_run",
        "month": "2026-08",
    }
    response = client.post("/api/v1/kpi/drilldown", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["level"] == "weekly"
    assert len(data["summary"]) == 2

    # Level 2 drilldown
    payload["week"] = 1
    response_l2 = client.post("/api/v1/kpi/drilldown", json=payload)
    assert response_l2.status_code == 200
    data_l2 = response_l2.get_json()
    assert data_l2["level"] == "daily"
