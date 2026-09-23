import logging
import os
import sys
import time
import tracemalloc
from typing import Any
import numpy as np
import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

from app.services.file_parser import parse_file
from app.services.automation_run import automation_run_answer, aggregate_automation_runs
from app.services.kpi_aggregator import aggregate_kpi_averages
from app.services.kpi_calculator import compute_df_kpis, compute_row_kpis
from app.utils.time_utils import parse_datetime
from app.services.automation_rca_conclusion import summarize_automation_rca_conclusion
from app.services.drilldown_service import get_table_drilldown
from app.services.global_filter_service import (
    get_available_filter_options,
    validate_and_normalize_filters,
)
from app.services.export_service import generate_excel_export, generate_csv_export
from app.services.cache_service import (
    save_to_cache,
    get_from_cache,
    get_cached_export_payload,
)

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
    try:
        current, _ = tracemalloc.get_traced_memory()
        return current / (1024.0 * 1024.0)
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

        # 2. Validate file extension (.xlsx, .xls, .csv, .zip)
        if not (filename.endswith(".xlsx") or filename.endswith(".xls") or filename.endswith(".csv") or filename.endswith(".zip")):
            logger.warning(f"❌ [API 1: INVALID FILE TYPE] Filename '{file.filename}' is not .xlsx, .xls, .csv, or .zip.")
            return jsonify({"error": "File must be an .xlsx, .xls, .csv, or .zip file"}), 400

        # 3. Parse file into normalized dictionary rows using multi-engine fallback
        logger.info("🔄 [API 1: PARSING FILE] Ingesting headers and extracting data rows...")
        parse_result = parse_file(file, filename=file.filename)
        if not parse_result["success"]:
            logger.error(f"❌ [API 1: PARSE ERROR] Excel parsing failed: {parse_result['error']}")
            return jsonify({"error": parse_result["error"]}), 400

        df = parse_result.get("df")
        global_warnings: list[str] = []

        if df is not None and not df.empty:
            df_kpi, global_warnings = compute_df_kpis(df)
            row_count = len(df_kpi)
            df_kpi["row_index"] = list(range(2, row_count + 2))

            for col in ["SRNUMBER", "SRCREATIONTIME", "AUTOMATION_RCA_CONCLUSION", "AUTOMATION_RUN"]:
                if col not in df_kpi.columns:
                    df_kpi[col] = None

            df_kpi["SRNUMBER"] = df_kpi["SRNUMBER"].apply(_format_str)
            df_kpi["SRCREATIONTIME"] = df_kpi["SRCREATIONTIME"].apply(_format_date)
            df_kpi["AUTOMATION_RCA_CONCLUSION"] = df_kpi["AUTOMATION_RCA_CONCLUSION"].apply(_format_str)
            df_kpi["AUTOMATION_RUN"] = df_kpi["AUTOMATION_RUN"].apply(automation_run_answer)

            if "warnings" not in df_kpi.columns:
                df_kpi["warnings"] = [[] for _ in range(row_count)]

            out_cols = [
                "row_index",
                "SRNUMBER",
                "SRCREATIONTIME",
                "AUTOMATION_RCA_CONCLUSION",
                "AUTOMATION_RUN",
                "MTTI",
                "MTTA",
                "MTTAck",
                "MTTR",
                "MTTr",
                "warnings",
            ]
            
            df_kpi_out = df_kpi[out_cols].where(pd.notna(df_kpi[out_cols]), None)
            processed_rows = df_kpi_out.to_dict(orient="records")
            total_warnings = sum(len(r.get("warnings") or []) for r in processed_rows)
        else:
            raw_rows = parse_result["rows"]
            row_count = len(raw_rows)
            logger.info(f"✅ [API 1: FILE PARSED SUCCESSFULLY] Extracted {row_count} data rows.")

            processed_rows = []
            total_warnings = 0

            for idx, row in enumerate(raw_rows):
                computed = compute_row_kpis(row)
                warnings_list = computed.get("warnings", [])
                total_warnings += len(warnings_list)

                formatted_row = {
                    "row_index": idx + 2,
                    "SRNUMBER": _format_str(row.get("SRNUMBER")),
                    "SRCREATIONTIME": _format_date(row.get("SRCREATIONTIME")),
                    "AUTOMATION_RCA_CONCLUSION": _format_str(row.get("AUTOMATION_RCA_CONCLUSION")),
                    "AUTOMATION_RUN": automation_run_answer(row.get("AUTOMATION_RUN")),
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

        upload_id = save_to_cache(processed_rows)

        return (
            jsonify(
                {
                    "upload_id": upload_id,
                    "row_count": len(processed_rows),
                    "rows": processed_rows,
                    "global_warnings": global_warnings,
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


@api_bp.route("/kpi/automation-run", methods=["POST"], strict_slashes=False)
def check_automation_run():
    """API 3: Count automation Y/N values from the upload API JSON response."""
    start_time = time.perf_counter()
    group_by = request.args.get("group_by", "daily").lower().strip()
    if group_by not in {"daily", "weekly", "monthly"}:
        return jsonify({"error": "group_by must be one of: daily, weekly, monthly"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must contain the JSON response from /kpi/upload"}), 400

    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return jsonify({"error": "JSON payload must contain a 'rows' array"}), 400

    result = aggregate_automation_runs(rows, group_by)
    duration = (time.perf_counter() - start_time) * 1000
    logger.info(
        "[API 3 PERFORMANCE COUNTER] Automation run completed in %.3f ms "
        "(group_by='%s', records=%d, periods=%d)",
        duration,
        group_by,
        len(rows),
        result.get("periods_count", 0),
    )
    return jsonify(result), 200

@api_bp.route("/kpi/automation-rca-conclusion", methods=["POST"], strict_slashes=False)
def check_automation_rca_conclusion():
    """Count automation RCA conclusion Y/N values from the JSON returned by the upload API."""
    group_by = request.args.get("group_by", "daily").lower().strip()
    if group_by not in {"daily", "weekly", "monthly"}:
        return jsonify({"error": "group_by must be one of: daily, weekly, monthly"}), 400

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Request body must contain the JSON response from /kpi/upload"}), 400

    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return jsonify({"error": "JSON payload must contain a 'rows' array"}), 400

    return jsonify(summarize_automation_rca_conclusion(rows, group_by)), 200


@api_bp.route("/kpi/drilldown", methods=["POST"], strict_slashes=False)
def handle_table_drilldown():
    """
    2-Level Drill-Down Endpoint
    ---------------------------
    Level 1: Month -> 4 Weeks breakdown (when week is omitted)
    Level 2: Week -> 7 Days Daily breakdown for specified week number
    """
    data = request.get_json(silent=True) or {}
    rows = data.get("rows")
    if not isinstance(rows, list):
        return jsonify({"error": "JSON payload must contain a 'rows' array"}), 400

    table_type = request.args.get("table_type") or data.get("table_type", "avg")
    month = request.args.get("month") or data.get("month")
    week = request.args.get("week") or data.get("week")

    if not month:
        return jsonify({"error": "Query parameter or payload field 'month' is required (e.g. '2026-08' or 'August 2026')"}), 400

    drilldown_data = get_table_drilldown(rows=rows, table_type=table_type, month=month, week=week)
    return jsonify(drilldown_data), 200


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


# ==============================================================================
# GLOBAL FILTER API ENDPOINTS
# ==============================================================================
# Centralized endpoints for fetching available global filter options (e.g. daily,
# weekly, monthly) and validating active filter payloads across all summary tables.
# ==============================================================================

@api_bp.route("/kpi/global-filter/options", methods=["GET"], strict_slashes=False)
def get_global_filter_options():
    """Returns available filter options and metadata for the top navbar Global Filter UI."""
    return jsonify(get_available_filter_options()), 200


@api_bp.route("/kpi/global-filter/validate", methods=["POST"], strict_slashes=False)
def validate_global_filters():
    """Validates and normalizes incoming global filter parameters."""
    data = request.get_json(silent=True) or {}
    normalized = validate_and_normalize_filters(data)
    return jsonify({"success": True, "filters": normalized}), 200


# ==============================================================================
# EXPORT API ENDPOINT
# ==============================================================================
# Accepts table/chart data and streams back professionally styled Excel or CSV files.
# ==============================================================================

@api_bp.route("/kpi/export", methods=["POST"], strict_slashes=False)
@api_bp.route("/export", methods=["POST"], strict_slashes=False)
def export_table_or_chart_data():
    """
    Export Endpoint: Generates and streams back styled Excel (.xlsx) or CSV (.csv) files.
    JSON Body:
    {
        "format": "xlsx" | "csv" (default "xlsx"),
        "filename": "unified_kpi_summary",
        "sheet_name": "KPI Summary",
        "title": "Unified KPI Report",
        "columns": [{"key": "period", "label": "Time Period"}, ...],
        "data": [...]
    }
    """
    import re

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must contain valid JSON object"}), 400

    export_format = str(data.get("format", "xlsx")).lower().strip()
    if export_format not in {"xlsx", "csv"}:
        return jsonify({"error": f"Invalid export format '{export_format}'. Supported formats are: 'xlsx', 'csv'"}), 400

    raw_filename = str(data.get("filename") or "kpi_export").strip()
    # Sanitize filename
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", raw_filename) or "kpi_export"
    if safe_filename.lower().endswith(f".{export_format}"):
        safe_filename = safe_filename[:-(len(export_format) + 1)]

    sheet_name = str(data.get("sheet_name") or "Export").strip()
    title = data.get("title")

    rows = data.get("data")
    if rows is None:
        return jsonify({"error": "Payload missing 'data' array"}), 400
    if not isinstance(rows, list):
        return jsonify({"error": "'data' field must be an array of objects"}), 400

    columns = data.get("columns")
    if not columns or not isinstance(columns, list):
        if rows and isinstance(rows[0], dict):
            columns = [{"key": k, "label": str(k).replace("_", " ").title()} for k in rows[0].keys()]
        else:
            return jsonify({"error": "Must provide a non-empty 'columns' array or non-empty 'data'"}), 400

    try:
        if export_format == "xlsx":
            buffer = generate_excel_export(
                columns=columns,
                data=rows,
                title=title,
                sheet_name=sheet_name,
            )
            download_filename = f"{safe_filename}.xlsx"
            return send_file(
                buffer,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=download_filename,
            )
        else:
            buffer = generate_csv_export(
                columns=columns,
                data=rows,
            )
            download_filename = f"{safe_filename}.csv"
            return send_file(
                buffer,
                mimetype="text/csv; charset=utf-8",
                as_attachment=True,
                download_name=download_filename,
            )
    except Exception as exc:
        logger.error(f"❌ [EXPORT ERROR] Failed to generate {export_format} export: {exc}", exc_info=True)
        return jsonify({"error": f"Export generation error: {str(exc)}"}), 500


@api_bp.route("/kpi/cache", methods=["GET"], strict_slashes=False)
def get_cache_status():
    """Returns current cache status and metadata for latest or specified upload_id."""
    upload_id = request.args.get("upload_id")
    cached = get_from_cache(upload_id)
    if not cached:
        return jsonify({"status": "empty", "message": "No data currently cached."}), 200
    return jsonify({
        "status": "cached",
        "upload_id": cached.get("upload_id"),
        "timestamp": cached.get("timestamp"),
        "row_count": cached.get("row_count", 0),
    }), 200


@api_bp.route("/kpi/export/cache", methods=["GET", "POST"], strict_slashes=False)
@api_bp.route("/export/cache", methods=["GET", "POST"], strict_slashes=False)
def export_from_cache():
    """
    Downloads Excel or CSV directly from the server-side in-memory cached dataset.
    Parameters (supported via URL query string OR JSON body):
      - type / table_type: 'avg' (default) | 'automation_run' | 'automation_rca' | 'raw' | 'bucket'
      - period: 'monthly' (default) | 'weekly' | 'daily'
      - format: 'xlsx' (default) | 'csv'
      - upload_id: optional cache identifier
      - filename: optional custom filename
    """
    import re

    # Extract parameters from query args or JSON body
    if request.method == "POST" and request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.args.to_dict()

    table_type = data.get("table_type") or data.get("type", "avg")
    period = data.get("period") or data.get("group_by", "monthly")
    export_format = str(data.get("format", "xlsx")).lower().strip()
    upload_id = data.get("upload_id")

    if export_format not in {"xlsx", "csv"}:
        return jsonify({"error": f"Invalid export format '{export_format}'. Supported formats: 'xlsx', 'csv'"}), 400

    try:
        columns, rows, default_title, default_filename = get_cached_export_payload(
            table_type=table_type,
            period=period,
            upload_id=upload_id,
        )
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 404
    except Exception as exc:
        logger.error(f"❌ [CACHE EXPORT ERROR] Failed to retrieve cached data: {exc}", exc_info=True)
        return jsonify({"error": f"Cache retrieval error: {str(exc)}"}), 500

    raw_filename = str(data.get("filename") or default_filename).strip()
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", raw_filename) or default_filename
    if safe_filename.lower().endswith(f".{export_format}"):
        safe_filename = safe_filename[:-(len(export_format) + 1)]

    sheet_name = str(data.get("sheet_name") or default_title[:30]).strip()
    title = data.get("title") or default_title

    try:
        if export_format == "xlsx":
            buffer = generate_excel_export(
                columns=columns,
                data=rows,
                title=title,
                sheet_name=sheet_name,
            )
            download_filename = f"{safe_filename}.xlsx"
            return send_file(
                buffer,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name=download_filename,
            )
        else:
            buffer = generate_csv_export(
                columns=columns,
                data=rows,
            )
            download_filename = f"{safe_filename}.csv"
            return send_file(
                buffer,
                mimetype="text/csv; charset=utf-8",
                as_attachment=True,
                download_name=download_filename,
            )
    except Exception as exc:
        logger.error(f"❌ [EXPORT CACHE ERROR] Failed generating {export_format}: {exc}", exc_info=True)
        return jsonify({"error": f"Export error: {str(exc)}"}), 500



