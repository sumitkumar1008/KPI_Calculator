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


def test_nstt_upload_file_mismatch_missing_columns(client):
    # Namo file missing required columns
    bad_namo_csv = "INCIDENTID,FACTORY\nINC001,IM\n"
    good_remedy_csv = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,INCIDENT_IMPACT,DESCRIPTION\n"
        "INC001,ANG Technologies,2026-09-01 12:00:00,2026-09-01 09:30:00,0,Ring Failure\n"
    )

    data = {
        "namo_file": (io.BytesIO(bad_namo_csv.encode("utf-8")), "bad_namo.csv"),
        "remedy_file": (io.BytesIO(good_remedy_csv.encode("utf-8")), "remedy.csv"),
    }

    res = client.post("/api/v1/nstt/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["error_type"] == "FILE_MISMATCH"
    assert "File Mismatch Error" in json_data["error"]
    assert len(json_data["missing_columns"]) > 0
    assert "ATTRIBUTEDTO" in json_data["missing_columns"]
    assert "internal_error" in json_data


def test_nstt_upload_file_mismatch_swapped_files(client):
    # User puts Remedy file into Namo slot and Namo into Remedy
    namo_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
        "INC001,TXN,2026-09-01 10:00:00,IM,yes,INC001,Text\n"
    )
    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,INCIDENT_IMPACT,DESCRIPTION\n"
        "INC001,ANG,2026-09-01 12:00:00,2026-09-01 09:30:00,0,Desc\n"
    )

    data = {
        "namo_file": (io.BytesIO(remedy_content.encode("utf-8")), "swapped_remedy.csv"),
        "remedy_file": (io.BytesIO(namo_content.encode("utf-8")), "swapped_namo.csv"),
    }

    res = client.post("/api/v1/nstt/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["error_type"] == "FILE_MISMATCH"
    assert "File Mismatch Error" in json_data["error"]
    assert "appears to be a Remedy Report" in json_data["internal_error"]
    assert len(json_data["missing_columns"]) > 0
    assert "internal_error" in json_data


def test_nstt_upload_independent_of_filenames(client):
    # Files with completely arbitrary names (no 'namo' or 'remedy' in the filename)
    namo_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
        "INC001,TXN,2026-09-01 10:00:00,IM,yes,INC001,Text\n"
    )
    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,INCIDENT_IMPACT,DESCRIPTION\n"
        "INC001,ANG,2026-09-01 12:00:00,2026-09-01 09:30:00,0,Desc\n"
    )

    data = {
        "namo_file": (io.BytesIO(namo_content.encode("utf-8")), "arbitrary_dataset_alpha.csv"),
        "remedy_file": (io.BytesIO(remedy_content.encode("utf-8")), "custom_export_beta.csv"),
    }

    res = client.post("/api/v1/nstt/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    json_data = res.get_json()
    assert "upload_id" in json_data
    assert json_data["stats"]["namo_rows"] == 1


def test_nstt_upload_both_files_missing_columns(client):
    # Both files missing required columns with arbitrary filenames
    bad_file1 = "INCIDENTID,SOME_COL\nINC001,Val\n"
    bad_file2 = "INCIDENT_NUMBER,OTHER_COL\nINC001,Val2\n"

    data = {
        "namo_file": (io.BytesIO(bad_file1.encode("utf-8")), "raw_dump_1.csv"),
        "remedy_file": (io.BytesIO(bad_file2.encode("utf-8")), "raw_dump_2.csv"),
    }

    res = client.post("/api/v1/nstt/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["error_type"] == "FILE_MISMATCH"
    assert "File Mismatch Error" in json_data["error"]
    assert "files" in json_data
    assert json_data["files"]["file1"]["status"] == "mismatch"
    assert json_data["files"]["file2"]["status"] == "mismatch"
    assert len(json_data["files"]["file1"]["missing_columns"]) > 0
    assert len(json_data["files"]["file2"]["missing_columns"]) > 0
    assert "internal_error" in json_data

