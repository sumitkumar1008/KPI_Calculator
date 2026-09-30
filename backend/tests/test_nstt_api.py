import io
import pytest


def test_nstt_health(client):
    res = client.get("/api/v1/nstt/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["module"] == "nstt_analytics"


def test_nstt_upload_missing_files(client):
    # No files in request
    res = client.post("/api/v1/nstt/upload", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "Missing required 'namo_file'" in res.get_json()["error"]


def test_nstt_upload_success_and_master_fetch(client):
    namo_csv = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT,EXTRA_NAMO_COL\n"
        "INC001,TXN,2026-09-01 10:00:00,IM,yes,INC001,FLT Observations for Unstitched LSI,Val1\n"
        "INC002,TNL,2026-09-01 11:00:00,Non IM,no,,No Issue,Val2\n"
        "INC001,TXN,2026-09-01 10:00:00,IM,yes,INC001,FLT Observations for Unstitched LSI,Val3\n"
    )
    remedy_csv = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,INCIDENT_IMPACT,DESCRIPTION,EXTRA_REMEDY\n"
        "INC001,ANG Technologies,2026-09-01 12:00:00,2026-09-01 09:30:00,0,Ring Failure,RemedyVal1\n"
    )

    data = {
        "namo_file": (io.BytesIO(namo_csv.encode("utf-8")), "namo.csv"),
        "remedy_file": (io.BytesIO(remedy_csv.encode("utf-8")), "remedy.csv"),
    }

    res = client.post("/api/v1/nstt/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    json_data = res.get_json()

    assert "upload_id" in json_data
    assert "master_response" in json_data
    assert "stats" in json_data

    stats = json_data["stats"]
    assert stats["namo_rows"] == 3
    assert stats["remedy_rows"] == 1
    assert stats["matched"] == 2  # 2 rows of INC001 matched
    assert stats["unmatched"] == 1  # 1 row of INC002 unmatched
    assert stats["duplicates"] == 2  # 2 duplicate rows for INC001

    records = json_data["master_response"]["records"]
    assert len(records) == 3

    # Check INCIDENT_IMPACT mapping: 0 -> "SA"
    assert records[0]["INCIDENT_IMPACT"] == "SA"
    # Check extra Namo column preserved
    assert records[0]["EXTRA_NAMO_COL"] == "Val1"
    # Check Remedy column appended
    assert records[0]["ASSIGNED_SUPPORT_COMPANY"] == "ANG Technologies"

    # Test GET /api/v1/nstt/master with upload_id
    upload_id = json_data["upload_id"]
    master_res = client.get(f"/api/v1/nstt/master?upload_id={upload_id}")
    assert master_res.status_code == 200
    assert master_res.get_json()["master_response"]["total_records"] == 3
