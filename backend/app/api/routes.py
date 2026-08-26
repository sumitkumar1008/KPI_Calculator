"""
API Routes & Controller Endpoints
=================================
This module defines the primary HTTP endpoints for the KPI calculation service.

Endpoints:
----------
POST /api/v1/kpi/upload
    Ingests an uploaded Excel spreadsheet (.xlsx or binary .xls), extracts required
    timestamp columns, computes the 5 key performance metrics (MTTI, MTTA, MTTAck, MTTR, MTTr)
    for every row, and returns a streamlined JSON payload for frontend table rendering.
"""

from typing import Any
from flask import Blueprint, jsonify, request

from app.services.excel_parser import parse_excel_file
from app.services.kpi_aggregator import aggregate_kpi_averages
from app.services.kpi_calculator import compute_row_kpis
from app.utils.time_utils import parse_datetime

# Initialize Flask Blueprint with API versioning prefix (/api/v1)
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _format_date(val: Any) -> str | None:
    """Helper: Parses a datetime value and formats it as an ISO-8601 string (YYYY-MM-DDTHH:MM:SS)."""
    dt = parse_datetime(val)
    if dt is None:
        return None
    return dt.isoformat()


def _format_str(val: Any) -> str | None:
    """Helper: Cleans and returns string values (e.g. SRNUMBER), handling empty/None/NaN cases."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() == "nan" or s.lower() == "none":
        return None
    return s


@api_bp.route("/kpi/upload", methods=["POST"], strict_slashes=False)
def upload_kpi_excel():
    """
    Excel Upload & KPI Calculation Endpoint
    ---------------------------------------
    Accepts: multipart/form-data upload containing an Excel file (.xlsx or .xls) under key 'file'.
    
    Processing Steps:
    1. Validates presence of attached file in request.
    2. Validates file extension (.xlsx or .xls).
    3. Calls excel_parser to parse sheet headers, perform column mapping, and extract data rows.
    4. Iterates over rows, computing the 5 metrics:
       - MTTI   = AUTOMATION_END_TIME - SRCREATIONTIME
       - MTTA   = ROSTER_ALLOCATION_TIME - SRCREATIONTIME
       - MTTAck = FIRST_ACKNOWLEDGEMENT_TIME - ROSTER_ALLOCATION_TIME
       - MTTR   = RESOLVEDTIME - SRCREATIONTIME
       - MTTr   = CIRCUIT_UPTIME - SRCREATIONTIME (or CREATIONTIME)
    5. Returns lightweight, frontend-ready JSON containing row count, array of calculated rows, and warnings.
    """
    # 1. Verify multipart form-data request contains file attachment
    if not request.files:
        return jsonify({"error": "No file field in request. Ensure Body is set to form-data and a file is attached."}), 400

    # Auto-detect file attached under key 'file' (or pick first attached file for flexibility)
    file = request.files.get("file") or next(iter(request.files.values()), None)
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # 2. Validate file extension
    filename = file.filename.lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        return jsonify({"error": "File must be an .xlsx or .xls Excel file"}), 400

    # 3. Parse Excel file into normalized dictionary rows using multi-engine fallback
    parse_result = parse_excel_file(file)
    if not parse_result["success"]:
        return jsonify({"error": parse_result["error"]}), 400

    raw_rows = parse_result["rows"]
    processed_rows: list[dict[str, Any]] = []

    # 4. Calculate KPIs for each row in the Excel sheet
    for idx, row in enumerate(raw_rows):
        computed = compute_row_kpis(row)     
        
        # Build clean frontend row object containing SRNUMBER, SRCREATIONTIME, and 5 KPI results
        formatted_row = {
            "row_index": idx + 2,  # Header row is index 1; data rows start at row 2
            "SRNUMBER": _format_str(row.get("SRNUMBER")),
            "SRCREATIONTIME": _format_date(row.get("SRCREATIONTIME")),
            "MTTI": computed["kpis"]["MTTI"],     # Mean Time To Involve (Automation End - Creation)
            "MTTA": computed["kpis"]["MTTA"],     # Mean Time To Allocate (Roster Allocation - Creation)
            "MTTAck": computed["kpis"]["MTTAck"], # Mean Time To Acknowledge (First Ack - Allocation)
            "MTTR": computed["kpis"]["MTTR"],     # Mean Time To Resolve (Resolved - Creation)
            "MTTr": computed["kpis"]["MTTr"],     # Mean Time To Restore (Circuit Uptime - Creation)
            "warnings": computed["warnings"],    # Row-level data quality warnings (e.g. missing date, negative duration)
        }
        processed_rows.append(formatted_row)

    # 5. Return JSON payload
    return (
        jsonify(
            {
                "row_count": len(processed_rows),
                "rows": processed_rows,
                "global_warnings": [],
            }
        ),
        200,
    )


@api_bp.route("/kpi/summary", methods=["POST"], strict_slashes=False)
def calculate_kpi_summary():
    """
    Sub-Millisecond Period-Wise KPI Summary Endpoint
    -------------------------------------------------
    Accepts:
    - JSON payload containing the calculated rows from API 1:
      Either {"rows": [...]} or direct array of rows [...].
    - Query parameter 'group_by': 'daily', 'weekly', or 'monthly' (default 'monthly').
    
    Processing Steps:
    1. Validates query parameter 'group_by' (must be 'daily', 'weekly', or 'monthly').
    2. Validates JSON payload presence.
    3. Extracts rows list.
    4. Calls kpi_aggregator.aggregate_kpi_averages() using pre-calculated row KPI seconds.
    5. Returns period summary JSON containing AVG_MTTI, AVG_MTTA, AVG_MTTAck, AVG_MTTR, AVG_MTTr.
    """
    # 1. Validate query parameter 'group_by'
    group_by = request.args.get("group_by", "monthly").lower().strip()
    valid_group_bys = {"daily", "weekly", "monthly"}
    if group_by not in valid_group_bys:
        return (
            jsonify(
                {
                    "error": f"Invalid group_by parameter '{group_by}'. Must be one of: daily, weekly, monthly"
                }
            ),
            400,
        )

    # 2. Extract JSON payload from request body (force=True allows flexible header handling in Postman/curl)
    data = request.get_json(silent=True, force=True)
    if data is None:
        return (
            jsonify(
                {
                    "error": "Request body must contain valid JSON. Ensure Body is set to raw JSON."
                }
            ),
            400,
        )

    # Extract rows list from payload (handles {"rows": [...]} or direct list [...])
    if isinstance(data, dict):
        rows = data.get("rows")
    elif isinstance(data, list):
        rows = data
    else:
        rows = None

    if rows is None or not isinstance(rows, list):
        return (
            jsonify(
                {
                    "error": "JSON payload must contain a 'rows' array or be a list of row objects"
                }
            ),
            400,
        )

    # 3. Compute period averages using kpi_aggregator service
    summary_result = aggregate_kpi_averages(rows, group_by=group_by)
    return jsonify(summary_result), 200
