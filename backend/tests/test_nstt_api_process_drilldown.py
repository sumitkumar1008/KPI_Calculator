"""
API Tests for NSTT Process, Summary, and Drill-down Routes
==========================================================
Verifies:
  - POST /api/v1/nstt/process classifies records and returns aggregated_result
  - GET /api/v1/nstt/summary returns cached hierarchical aggregation
  - POST /api/v1/nstt/drilldown returns filtered records for given category
"""

import pytest
from app import create_app
from app.services.nstt.cache_store import clear_nstt_cache, save_nstt_to_cache


@pytest.fixture
def app():
    clear_nstt_cache()
    app = create_app({"TESTING": True, "DEBUG": False})
    yield app
    clear_nstt_cache()


@pytest.fixture
def client(app):
    return app.test_client()


def test_process_with_inline_master_response(client):
    master_response = {
        "records": [
            {
                "INCIDENTID": "INC001",
                "ATTRIBUTEDTO": "TXN",
                "SRCREATIONTIME": "2026-01-01 10:00:00",
                "FACTORY": "IM",
                "AUTO_ALLOCATION": "yes",
                "AUTOMATION_UPDATE_NSTT_NUMBER": "INC001",
                "AUTOMATION_RCA_CONCLUSION_TEXT": "",
                "ASSIGNED_SUPPORT_COMPANY": "XYZ",
                "UP_TIME": "2026-01-01 12:00:00",
                "Submit Date": "2026-01-01 09:00:00",
                "INCIDENT_IMPACT": "SA",
                "DESCRIPTION": "",
            },
            {
                "INCIDENTID": "INC002",
                "ATTRIBUTEDTO": "TNL",
                "SRCREATIONTIME": "2026-01-01 10:00:00",
                "FACTORY": "Non IM",
                "AUTO_ALLOCATION": "no",
                "AUTOMATION_UPDATE_NSTT_NUMBER": None,
                "AUTOMATION_RCA_CONCLUSION_TEXT": "",
                "ASSIGNED_SUPPORT_COMPANY": "XYZ",
                "UP_TIME": "2026-01-01 12:00:00",
                "Submit Date": "2026-01-01 09:00:00",
                "INCIDENT_IMPACT": "NSA",
                "DESCRIPTION": "Fiber Section cut occurred",
            },
        ],
        "total_records": 2,
    }

    resp = client.post("/api/v1/nstt/process", json={"master_response": master_response})
    assert resp.status_code == 200
    data = resp.get_json()

    assert "classified_master_response" in data
    assert "aggregated_result" in data
    agg = data["aggregated_result"]
    assert agg["total_sr"] == 2
    assert agg["nstt_count"] == 2
    assert agg["automation"]["count"] == 1
    assert agg["manual"]["count"] == 1
    assert agg["failures"]["section_failure"] == 1


def test_process_with_cached_upload_id(client):
    master_response = {
        "records": [
            {
                "INCIDENTID": "INC001",
                "ATTRIBUTEDTO": "TXN",
                "SRCREATIONTIME": "2026-01-01 10:00:00",
                "FACTORY": "IM",
                "AUTO_ALLOCATION": "yes",
                "AUTOMATION_UPDATE_NSTT_NUMBER": "INC001",
                "AUTOMATION_RCA_CONCLUSION_TEXT": "",
                "ASSIGNED_SUPPORT_COMPANY": "XYZ",
                "UP_TIME": "2026-01-01 12:00:00",
                "Submit Date": "2026-01-01 09:00:00",
                "INCIDENT_IMPACT": "SA",
                "DESCRIPTION": "",
            }
        ],
        "total_records": 1,
    }

    upload_id = save_nstt_to_cache(master_response, stats={"matched": 1})

    resp = client.post("/api/v1/nstt/process", json={"upload_id": upload_id})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["upload_id"] == upload_id
    assert data["aggregated_result"]["total_sr"] == 1


def test_get_summary_endpoint(client):
    master_response = {
        "records": [
            {
                "INCIDENTID": "INC001",
                "ATTRIBUTEDTO": "TXN",
                "SRCREATIONTIME": "2026-01-01 10:00:00",
                "FACTORY": "IM",
                "AUTO_ALLOCATION": "yes",
                "AUTOMATION_UPDATE_NSTT_NUMBER": "INC001",
                "AUTOMATION_RCA_CONCLUSION_TEXT": "",
                "ASSIGNED_SUPPORT_COMPANY": "XYZ",
                "UP_TIME": "2026-01-01 12:00:00",
                "Submit Date": "2026-01-01 09:00:00",
                "INCIDENT_IMPACT": "SA",
                "DESCRIPTION": "",
            }
        ],
        "total_records": 1,
    }

    upload_id = save_nstt_to_cache(master_response, stats={"matched": 1})
    client.post("/api/v1/nstt/process", json={"upload_id": upload_id})

    resp = client.get(f"/api/v1/nstt/summary?upload_id={upload_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "aggregated_result" in data
    assert data["aggregated_result"]["total_sr"] == 1


def test_drilldown_endpoint(client):
    master_response = {
        "records": [
            {
                "INCIDENTID": "INC001",
                "ATTRIBUTEDTO": "TXN",
                "SRCREATIONTIME": "2026-01-01 10:00:00",
                "FACTORY": "IM",
                "AUTO_ALLOCATION": "yes",
                "AUTOMATION_UPDATE_NSTT_NUMBER": "INC001",
                "AUTOMATION_RCA_CONCLUSION_TEXT": "",
                "ASSIGNED_SUPPORT_COMPANY": "XYZ",
                "UP_TIME": "2026-01-01 12:00:00",
                "Submit Date": "2026-01-01 09:00:00",
                "INCIDENT_IMPACT": "SA",
                "DESCRIPTION": "",
            },
            {
                "INCIDENTID": "INC002",
                "ATTRIBUTEDTO": "TXN",
                "SRCREATIONTIME": "2026-01-01 10:00:00",
                "FACTORY": "IM",
                "AUTO_ALLOCATION": "no",
                "AUTOMATION_UPDATE_NSTT_NUMBER": "INC002",
                "AUTOMATION_RCA_CONCLUSION_TEXT": "",
                "ASSIGNED_SUPPORT_COMPANY": "XYZ",
                "UP_TIME": "2026-01-01 12:00:00",
                "Submit Date": "2026-01-01 09:00:00",
                "INCIDENT_IMPACT": "NSA",
                "DESCRIPTION": "",
            },
        ],
        "total_records": 2,
    }

    upload_id = save_nstt_to_cache(master_response, stats={"matched": 2})
    client.post("/api/v1/nstt/process", json={"upload_id": upload_id})

    # Drill down into IM Auto SA
    resp = client.post(
        "/api/v1/nstt/drilldown",
        json={"category": "automation.same_nstt.im.auto.sa", "upload_id": upload_id},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total_records"] == 1
    assert data["records"][0]["INCIDENTID"] == "INC001"
