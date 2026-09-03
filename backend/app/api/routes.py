import logging
import os
import sys
import time
import tracemalloc
from typing import Any
from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

from app.services.excel_parser import parse_excel_file
from app.services.kpi_aggregator import aggregate_kpi_averages
from app.services.kpi_calculator import compute_row_kpis
from app.utils.time_utils import parse_datetime

# Configure structured stdout logger for Render live console logs
logger = logging.getLogger("kpi_logger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [KPI-SERVER] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Initialize Flask Blueprint with API versioning prefix (/api/v1)
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def get_process_ram_mb() -> float:
    """Helper: Returns total process memory usage (Resident Set Size) in Megabytes (MB)."""
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return float(line.split()[1]) / 1024.0
        except Exception:
            pass
    return 0.0


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
    Excel Upload & KPI Calculation Endpoint (API 1)
    -----------------------------------------------
    Accepts: multipart/form-data upload containing an Excel file (.xlsx or .xls) under key 'file'.
    Clocks execution response time and peak RAM usage for heavy Excel payloads.
    """
    start_time = time.perf_counter()
    start_ram = get_process_ram_mb()
    tracemalloc.start()

    logger.info("==================================================")
    logger.info(f"📥 [API 1: UPLOAD INITIATED] Processing Excel upload. Start RAM: {start_ram:.2f} MB")

    try:
        # 1. Verify multipart form-data request contains file attachment
        if not request.files:
            logger.warning("❌ [API 1: REJECTED] Request contains no multipart file attachment.")
            return jsonify({"error": "No file field in request. Ensure Body is set to form-data and a file is attached."}), 400

        # Auto-detect file attached under key 'file' (or pick first attached file for flexibility)
        file = request.files.get("file") or next(iter(request.files.values()), None)
        if not file or file.filename == "":
            logger.warning("❌ [API 1: REJECTED] No file selected or empty filename.")
            return jsonify({"error": "No file selected"}), 400

        filename = file.filename.lower()
        logger.info(f"📄 [API 1: FILE RECEIVED] Filename: '{file.filename}'")

        # 2. Validate file extension
        if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
            logger.warning(f"❌ [API 1: INVALID FILE TYPE] Filename '{file.filename}' is not .xlsx or .xls.")
            return jsonify({"error": "File must be an .xlsx or .xls Excel file"}), 400

        # 3. Parse Excel file into normalized dictionary rows using multi-engine fallback
        logger.info("🔄 [API 1: PARSING EXCEL] Ingesting sheet headers and extracting data rows...")
        parse_result = parse_excel_file(file)
        if not parse_result["success"]:
            logger.error(f"❌ [API 1: PARSE ERROR] Excel parsing failed: {parse_result['error']}")
            return jsonify({"error": parse_result["error"]}), 400

        raw_rows = parse_result["rows"]
        row_count = len(raw_rows)
        logger.info(f"✅ [API 1: EXCEL PARSED SUCCESSFULLY] Extracted {row_count} data rows.")

        # 4. Calculate KPIs for each row in the Excel sheet
        processed_rows: list[dict[str, Any]] = []
        total_warnings = 0

        for idx, row in enumerate(raw_rows):
            computed = compute_row_kpis(row)
            warnings_list = computed.get("warnings", [])
            total_warnings += len(warnings_list)

            formatted_row = {
                "row_index": idx + 2,  # Header row is index 1; data rows start at row 2
                "SRNUMBER": _format_str(row.get("SRNUMBER")),
                "SRCREATIONTIME": _format_date(row.get("SRCREATIONTIME")),
                "AUTOMATION_RCA_CONCLUSION": _format_str(row.get("AUTOMATION_RCA_CONCLUSION")),
                "AUTOMATION_RUN": _format_str(row.get("AUTOMATION_RUN")),
                "MTTI": computed["kpis"]["MTTI"],
                "MTTA": computed["kpis"]["MTTA"],
                "MTTAck": computed["kpis"]["MTTAck"],
                "MTTR": computed["kpis"]["MTTR"],
                "MTTr": computed["kpis"]["MTTr"],
                "warnings": warnings_list,
            }
            processed_rows.append(formatted_row)

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        duration = time.perf_counter() - start_time
        end_ram = get_process_ram_mb()
        peak_ram_mb = peak_mem / (1024 * 1024)

        logger.info(f"✅ [API 1: SUCCESS] Processed {len(processed_rows)} rows (Warnings: {total_warnings})")
        logger.info(
            f"⏱️ [API 1 PERFORMANCE COUNTER] "
            f"Response Time: {duration:.3f}s ({duration * 1000:.1f}ms) | "
            f"Peak Python RAM Allocated: {peak_ram_mb:.2f} MB | "
            f"Process RAM: {end_ram:.2f} MB"
        )

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

    except HTTPException:
        tracemalloc.stop()
        raise
    except Exception as exc:
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        duration = time.perf_counter() - start_time
        end_ram = get_process_ram_mb()
        peak_ram_mb = peak_mem / (1024 * 1024)

        logger.error(
            f"💥 [API 1: CRITICAL ERROR] Exception after {duration:.3f}s (Peak RAM: {peak_ram_mb:.2f} MB): "
            f"{type(exc).__name__}: {str(exc)}",
            exc_info=True,
        )
        return jsonify({"error": f"Upload Processing Error: {str(exc)}"}), 500


@api_bp.route("/kpi/summary", methods=["POST"], strict_slashes=False)
def calculate_kpi_summary():
    """
    Sub-Millisecond Period-Wise KPI Summary Endpoint (API 2)
    --------------------------------------------------------
    Groups row results by daily, weekly, or monthly and calculates non-null KPI averages.
    Clocks response time and peak RAM allocation for period summary aggregations.
    """
    start_time = time.perf_counter()
    start_ram = get_process_ram_mb()
    tracemalloc.start()

    logger.info("==================================================")

    try:
        # 1. Validate query parameter 'group_by'
        group_by = request.args.get("group_by", "monthly").lower().strip()
        logger.info(f"📊 [API 2: SUMMARY INITIATED] Filter: group_by='{group_by}'. Start RAM: {start_ram:.2f} MB")

        valid_group_bys = {"daily", "weekly", "monthly"}
        if group_by not in valid_group_bys:
            logger.warning(f"❌ [API 2: REJECTED] Invalid group_by parameter '{group_by}'.")
            return (
                jsonify(
                    {
                        "error": f"Invalid group_by parameter '{group_by}'. Must be one of: daily, weekly, monthly"
                    }
                ),
                400,
            )

        # 2. Extract JSON payload from request body
        data = request.get_json(silent=True, force=True)
        if data is None:
            logger.warning("❌ [API 2: REJECTED] Request body is empty or invalid JSON.")
            return (
                jsonify(
                    {
                        "error": "Request body must contain valid JSON. Ensure Body is set to raw JSON."
                    }
                ),
                400,
            )

        # Extract rows list from payload
        if isinstance(data, dict):
            rows = data.get("rows")
        elif isinstance(data, list):
            rows = data
        else:
            rows = None

        if rows is None or not isinstance(rows, list):
            logger.warning("❌ [API 2: REJECTED] Payload missing 'rows' array.")
            return (
                jsonify(
                    {
                        "error": "JSON payload must contain a 'rows' array or be a list of row objects"
                    }
                ),
                400,
            )

        logger.info(f"🧮 [API 2: AGGREGATING] Aggregating averages for {len(rows)} calculated rows...")

        # 3. Compute period averages using kpi_aggregator service
        summary_result = aggregate_kpi_averages(rows, group_by=group_by)
        periods_list = summary_result.get("summary", [])

        # Log detailed summary metrics for each period bucket
        logger.info(f"✅ [API 2: BUCKETS CREATED] Computed {len(periods_list)} period buckets for '{group_by}':")
        for p in periods_list:
            logger.info(
                f"   --> [{p.get('period_label')}] Total Records: {p.get('record_count')} | "
                f"Valid Counts: {p.get('valid_counts')} | "
                f"AVG_MTTI: {p.get('AVG_MTTI')} | AVG_MTTR: {p.get('AVG_MTTR')}"
            )

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        duration = time.perf_counter() - start_time
        end_ram = get_process_ram_mb()
        peak_ram_mb = peak_mem / (1024 * 1024)

        logger.info(
            f"⏱️ [API 2 PERFORMANCE COUNTER] "
            f"Response Time: {duration:.3f}s ({duration * 1000:.1f}ms) | "
            f"Peak Python RAM Allocated: {peak_ram_mb:.2f} MB | "
            f"Process RAM: {end_ram:.2f} MB"
        )

        return jsonify(summary_result), 200

    except HTTPException:
        tracemalloc.stop()
        raise
    except Exception as exc:
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        duration = time.perf_counter() - start_time
        end_ram = get_process_ram_mb()
        peak_ram_mb = peak_mem / (1024 * 1024)

        logger.error(
            f"💥 [API 2: CRITICAL ERROR] Exception after {duration:.3f}s (Peak RAM: {peak_ram_mb:.2f} MB): "
            f"{type(exc).__name__}: {str(exc)}",
            exc_info=True,
        )
        return jsonify({"error": f"Summary Calculation Error: {str(exc)}"}), 500
