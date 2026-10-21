import io
import pytest
from app.services.nstt.file_validator import validate_nstt_uploads, extract_file_headers


def test_validator_swapped_files_detection():
    namo_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,"
        "AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
        "INC1,TXN,2026-09-01,IM,yes,INC1,Done\n"
    ).encode("utf-8")

    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,"
        "INCIDENT_IMPACT,DESCRIPTION\n"
        "INC1,CompanyA,2026-09-01,2026-09-01,0,Desc\n"
    ).encode("utf-8")

    # Swapped: Remedy content in namo slot, Namo content in remedy slot
    result = validate_nstt_uploads(
        namo_file_input=io.BytesIO(remedy_content),
        remedy_file_input=io.BytesIO(namo_content),
        namo_filename="remedy_mistakenly_in_namo.csv",
        remedy_filename="namo_mistakenly_in_remedy.csv",
    )

    assert result["valid"] is False
    assert result["error_type"] == "SWAPPED_FILES"
    assert result["can_auto_swap"] is True
    assert "Datasets Are Swapped" in result["title"]
    assert len(result["namo_slot"]["missing_columns"]) > 0
    assert len(result["remedy_slot"]["missing_columns"]) > 0
    assert result["namo_slot"]["detected_as"] == "Remedy Report"
    assert result["remedy_slot"]["detected_as"] == "Namo Report"


def test_validator_correct_files():
    namo_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,"
        "AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
        "INC1,TXN,2026-09-01,IM,yes,INC1,Done\n"
    ).encode("utf-8")

    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,"
        "INCIDENT_IMPACT,DESCRIPTION\n"
        "INC1,CompanyA,2026-09-01,2026-09-01,0,Desc\n"
    ).encode("utf-8")

    result = validate_nstt_uploads(
        namo_file_input=io.BytesIO(namo_content),
        remedy_file_input=io.BytesIO(remedy_content),
        namo_filename="namo.csv",
        remedy_filename="remedy.csv",
    )

    assert result["valid"] is True
    assert result["can_auto_swap"] is False
    assert result["namo_slot"]["valid"] is True
    assert result["remedy_slot"]["valid"] is True


def test_api_validate_files_endpoint(client):
    namo_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,"
        "AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
    ).encode("utf-8")
    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,"
        "INCIDENT_IMPACT,DESCRIPTION\n"
    ).encode("utf-8")

    # Test swap detection via POST /api/v1/nstt/validate-files
    res = client.post(
        "/api/v1/nstt/validate-files",
        data={
            "namo_file": (io.BytesIO(remedy_content), "remedy_in_namo.csv"),
            "remedy_file": (io.BytesIO(namo_content), "namo_in_remedy.csv"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["valid"] is False
    assert data["error_type"] == "SWAPPED_FILES"
    assert data["can_auto_swap"] is True
    assert "recommendation" in data
    assert "namo_slot" in data
    assert "remedy_slot" in data


def test_api_upload_rejects_swapped_files(client):
    namo_content = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,"
        "AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
    ).encode("utf-8")
    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,"
        "INCIDENT_IMPACT,DESCRIPTION\n"
    ).encode("utf-8")

    # Post swapped files to upload endpoint
    res = client.post(
        "/api/v1/nstt/upload",
        data={
            "namo_file": (io.BytesIO(remedy_content), "remedy_in_namo.csv"),
            "remedy_file": (io.BytesIO(namo_content), "namo_in_remedy.csv"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    data = res.get_json()
    assert data["error_type"] == "SWAPPED_FILES"
    assert data["can_auto_swap"] is True
    assert "missing_columns" in data["namo_slot"]
    assert "missing_columns" in data["remedy_slot"]


def test_validator_with_title_banner():
    namo_content = (
        "TITLE: AIRTEL NAMO EXPORT\n"
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,"
        "AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
        "INC1,TXN,2026-09-01,IM,yes,INC1,Done\n"
    ).encode("utf-8")

    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,"
        "INCIDENT_IMPACT,DESCRIPTION\n"
        "INC1,CompanyA,2026-09-01,2026-09-01,0,Desc\n"
    ).encode("utf-8")

    result = validate_nstt_uploads(
        namo_file_input=io.BytesIO(namo_content),
        remedy_file_input=io.BytesIO(remedy_content),
        namo_filename="namo_with_title.csv",
        remedy_filename="remedy.csv",
    )
    assert result["valid"] is True


def test_validator_with_zip_file():
    import zipfile
    namo_csv = (
        "INCIDENTID,ATTRIBUTEDTO,SRCREATIONTIME,FACTORY,AUTO_ALLOCATION,"
        "AUTOMATION_UPDATE_NSTT_NUMBER,AUTOMATION_RCA_CONCLUSION_TEXT\n"
        "INC1,TXN,2026-09-01,IM,yes,INC1,Done\n"
    )
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("namo_inner.csv", namo_csv)
    zip_buf.seek(0)

    remedy_content = (
        "INCIDENT_NUMBER,ASSIGNED_SUPPORT_COMPANY,UP_TIME,Submit Date,"
        "INCIDENT_IMPACT,DESCRIPTION\n"
        "INC1,CompanyA,2026-09-01,2026-09-01,0,Desc\n"
    ).encode("utf-8")

    result = validate_nstt_uploads(
        namo_file_input=zip_buf,
        remedy_file_input=io.BytesIO(remedy_content),
        namo_filename="namo_data.zip",
        remedy_filename="remedy.csv",
    )
    assert result["valid"] is True

