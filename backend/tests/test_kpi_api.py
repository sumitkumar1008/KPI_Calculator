import io
import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def create_excel_bytes(data: dict[str, list]) -> io.BytesIO:
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    return buf


def test_upload_kpi_no_file_field(client):
    response = client.post("/api/v1/kpi/upload")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "No file field in request" in data["error"]


def test_upload_kpi_invalid_file_extension(client):
    data = {"file": (io.BytesIO(b"dummy text"), "test.txt")}
    response = client.post(
        "/api/v1/kpi/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    res_json = response.get_json()
    assert "File must be an" in res_json["error"]


def test_upload_kpi_missing_required_columns(client):
    incomplete_data = {
        "SRCREATIONTIME": ["2026-08-21 08:00:00"],
        "AUTOMATION_END_TIME": ["2026-08-21 14:00:00"],
    }
    excel_buf = create_excel_bytes(incomplete_data)
    data = {"file": (excel_buf, "test.xlsx")}

    response = client.post(
        "/api/v1/kpi/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    res_json = response.get_json()
    assert "Missing required Excel columns" in res_json["error"]


def test_upload_kpi_success_complete_flow(client):
    sample_excel = {
        "SR_NUMBER": ["SR-1001", "SR-1002"],
        "SRCREATIONTIME": ["2026-08-21 08:00:00", "2026-08-21 10:00:00"],
        "AUTOMATION_END_TIME": ["2026-08-21 14:00:00", "2026-08-21 18:00:00"],
        "ROSTER_ALLOCATION_TIME": ["2026-08-21 09:00:00", "2026-08-21 11:00:00"],
        "FIRST_ACKNOWLEDGEMENT_TIME": ["2026-08-21 09:30:00", "2026-08-21 11:30:00"],
        "RESOLVEDTIME": ["2026-08-22 12:00:00", "2026-08-22 14:00:00"],
        "CREATIONTIME": ["2026-08-20 10:00:00", "2026-08-20 12:00:00"],
        "CIRCUIT_UPTIME": ["2026-08-22 12:00:00", "2026-08-22 14:00:00"],
    }
    excel_buf = create_excel_bytes(sample_excel)
    data = {"file": (excel_buf, "sample_kpi.xlsx")}

    response = client.post(
        "/api/v1/kpi/upload",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    res_json = response.get_json()

    assert res_json["row_count"] == 2
    assert "rows" in res_json
    assert len(res_json["rows"]) == 2

    row1 = res_json["rows"][0]
    assert row1["row_index"] == 2
    assert row1["SRNUMBER"] == "SR-1001"
    assert "AUTOMATION_RCA_CONCLUSION" in row1
    assert "AUTOMATION_RUN" in row1
    assert row1["MTTI"] == "06:00:00"
    assert row1["MTTA"] == "01:00:00"
    assert row1["MTTAck"] == "00:30:00"
    assert row1["MTTR"] == "1d 04:00:00"
    assert row1["MTTr"] == "2d 02:00:00"

    row2 = res_json["rows"][1]
    assert row2["SRNUMBER"] == "SR-1002"
    assert "AUTOMATION_RCA_CONCLUSION" in row2
    assert "AUTOMATION_RUN" in row2


def test_upload_kpi_with_exact_automation_headers(client):
    sample_excel = {
        "SRNUMBER": ["SR-3001"],
        "SRCREATIONTIME": ["2026-08-21 08:00:00"],
        "AUTOMATION_END_TIME": ["2026-08-21 14:00:00"],
        "ROSTER_ALLOCATION_TIME": ["2026-08-21 09:00:00"],
        "FIRST_ACKNOWLEDGEMENT_TIME": ["2026-08-21 09:30:00"],
        "RESOLVEDTIME": ["2026-08-22 12:00:00"],
        "CREATIONTIME": ["2026-08-20 10:00:00"],
        "CIRCUIT_UPTIME": ["2026-08-22 12:00:00"],
        "AUTOMATION_RUN": ["Yes"],
        "AUTOMATION_RCA_CONCLUSION": ["Automated Triage Pass"],
    }
    excel_buf = create_excel_bytes(sample_excel)
    data = {"file": (excel_buf, "sample_exact.xlsx")}

    response = client.post(
        "/api/v1/kpi/upload",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    res_json = response.get_json()
    row = res_json["rows"][0]
    assert row["AUTOMATION_RUN"] == "Yes"
    assert row["AUTOMATION_RCA_CONCLUSION"] == "Automated Triage Pass"


def test_upload_kpi_payload_too_large_413(app, client):
    app.config["MAX_CONTENT_LENGTH"] = 100  # Set tiny limit for testing
    huge_data = {"file": (io.BytesIO(b"x" * 500), "huge.xlsx")}
    response = client.post(
        "/api/v1/kpi/upload",
        data=huge_data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
    res_json = response.get_json()
    assert "Uploaded file is too large" in res_json["error"]


def test_kpi_summary_monthly_success(client):
    payload = {
        "rows": [
            {
                "SRNUMBER": "SR-101",
                "SRCREATIONTIME": "2025-01-10T10:00:00",
                "MTTI": "00:06:00",
                "MTTI_seconds": 360,
                "MTTA": "00:01:00",
                "MTTA_seconds": 60,
                "MTTAck": "00:02:00",
                "MTTAck_seconds": 120,
                "MTTR": "1d 04:00:00",
                "MTTR_seconds": 100800,
                "MTTr": "2d 02:00:00",
                "MTTr_seconds": 180000,
            },
            {
                "SRNUMBER": "SR-102",
                "SRCREATIONTIME": "2025-01-20T14:00:00",
                "MTTI": "00:04:00",
                "MTTI_seconds": 240,
                "MTTA": "00:02:00",
                "MTTA_seconds": 120,
                "MTTAck": "00:02:00",
                "MTTAck_seconds": 120,
                "MTTR": "1d 02:00:00",
                "MTTR_seconds": 93600,
                "MTTr": "1d 10:00:00",
                "MTTr_seconds": 122400,
            },
        ]
    }

    response = client.post("/api/v1/kpi/summary?group_by=monthly", json=payload)
    assert response.status_code == 200
    res_json = response.get_json()

    assert res_json["group_by"] == "monthly"
    assert res_json["total_records"] == 2
    assert res_json["periods_count"] == 1
    summary = res_json["summary"][0]

    assert summary["period"] == "2025-01"
    assert summary["period_label"] == "January 2025"
    assert summary["record_count"] == 2
    assert summary["AVG_MTTI"] == "00:05:00"
    assert summary["AVG_MTTA"] == "00:01:30"
    assert summary["AVG_MTTAck"] == "00:02:00"
    assert summary["AVG_MTTR"] == "27:00:00"
    assert summary["AVG_MTTr"] == "42:00:00"


def test_kpi_summary_invalid_group_by(client):
    response = client.post("/api/v1/kpi/summary?group_by=yearly", json={"rows": []})
    assert response.status_code == 400
    res_json = response.get_json()
    assert "Invalid group_by parameter" in res_json["error"]


def test_kpi_summary_non_json_payload(client):
    response = client.post("/api/v1/kpi/summary", data="not json")
    assert response.status_code == 400
    res_json = response.get_json()
    assert "Request body must contain valid JSON" in res_json["error"]


