"""
NSTT API Routes
===============
Flask Blueprint providing endpoints for NSTT Analytics file ingestion,
VLOOKUP joining, impact conversion, Master Response generation,
Rule Engine classification, hierarchical aggregation, and drilldown.
"""

import logging
import sys
import time
from typing import Any, Dict, List, Optional
import pandas as pd
from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

from app.services.nstt.column_validator import validate_both_files_columns
from app.services.nstt.file_validator import validate_nstt_uploads
from app.services.nstt.namo_reader import parse_namo_file
from app.services.nstt.remedy_reader import parse_remedy_file
from app.services.nstt.vlookup import perform_vlookup
from app.services.nstt.impact_mapper import map_incident_impact
from app.services.nstt.duplicate_checker import check_duplicates
from app.services.nstt.master_builder import build_master_response
from app.services.nstt.rule_engine import run_rule_engine
from app.services.nstt.aggregator import build_nstt_aggregation, filter_records_by_category
from app.services.nstt.excel_generator import generate_nstt_excel_workbook
from app.services.nstt.cache_store import save_nstt_to_cache, get_nstt_from_cache
from app.services.export_service import generate_csv_export


# Logger for NSTT module
nstt_logger = logging.getLogger("nstt_logger")
nstt_logger.setLevel(logging.INFO)

if not nstt_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [NSTT-API] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    nstt_logger.addHandler(handler)

# Blueprint prefix: /api/v1/nstt
nstt_bp = Blueprint("nstt_api", __name__, url_prefix="/api/v1/nstt")


@nstt_bp.route("/health", methods=["GET"], strict_slashes=False)
def nstt_health():
    """Health check endpoint for NSTT module."""
    return jsonify({"status": "healthy", "module": "nstt_analytics"})


@nstt_bp.route("/validate-files", methods=["POST"], strict_slashes=False)
def validate_files_endpoint():
    """
    Fast pre-validation of uploaded Namo and Remedy files before upload.
    Detects swapped files, missing columns, and file format issues.
    """
    try:
        namo_keys = ["namo_file", "namo", "namofile", "namoFile", "namo_report", "namoReport"]
        namo_file = None
        for k in namo_keys:
            if k in request.files and request.files[k].filename:
                namo_file = request.files[k]
                break

        remedy_keys = ["remedy_file", "remedy", "remedyfile", "remedyFile", "remedy_report", "remedyReport"]
        remedy_file = None
        for k in remedy_keys:
            if k in request.files and request.files[k].filename:
                remedy_file = request.files[k]
                break

        result = validate_nstt_uploads(
            namo_file_input=namo_file,
            remedy_file_input=remedy_file,
            namo_filename=namo_file.filename if namo_file else "",
            remedy_filename=remedy_file.filename if remedy_file else "",
        )
        status_code = 200 if result.get("valid") else 400
        return jsonify(result), status_code
    except Exception as exc:
        import traceback
        nstt_logger.error(f"validate-files error: {str(exc)}\n{traceback.format_exc()}")
        return jsonify({
            "valid": False,
            "error": f"File validation failed: {str(exc)}",
            "error_type": "VALIDATION_ERROR",
        }), 400


@nstt_bp.route("/upload", methods=["POST"], strict_slashes=False)
def upload_nstt_files():
    """
    Ingests Namo and Remedy files, validates columns, executes VLOOKUP join,
    maps INCIDENT_IMPACT, flags duplicates, and constructs the Master Response JSON.
    """
    t_start = time.perf_counter()

    try:
        # Look for namo file under common key aliases
        namo_keys = ["namo_file", "namo", "namofile", "namoFile", "namo_report", "namoReport"]
        namo_file = None
        for k in namo_keys:
            if k in request.files and request.files[k].filename:
                namo_file = request.files[k]
                break

        # Look for remedy file under common key aliases
        remedy_keys = ["remedy_file", "remedy", "remedyfile", "remedyFile", "remedy_report", "remedyReport"]
        remedy_file = None
        for k in remedy_keys:
            if k in request.files and request.files[k].filename:
                remedy_file = request.files[k]
                break

        if not namo_file:
            return jsonify({
                "error": "Missing required 'namo_file' in form-data. Please attach the Namo Excel/CSV file with key 'namo_file'.",
                "error_type": "VALIDATION_ERROR",
            }), 400

        if not remedy_file:
            return jsonify({
                "error": "Missing required 'remedy_file' in form-data. Please attach the Remedy Excel/CSV file with key 'remedy_file'.",
                "error_type": "VALIDATION_ERROR",
            }), 400

        nstt_logger.info(f"Received NSTT files: File 1='{namo_file.filename}', File 2='{remedy_file.filename}'")

        # Step 1: Upfront column validation for BOTH files (independent of file names or slots)
        t_val_start = time.perf_counter()
        validation = validate_both_files_columns(
            file1_input=namo_file,
            file1_name=namo_file.filename,
            file2_input=remedy_file,
            file2_name=remedy_file.filename,
        )
        t_val_end = time.perf_counter()
        val_ms = round((t_val_end - t_val_start) * 1000, 2)

        if not validation["valid"]:
            nstt_logger.error(f"\n{validation['internal_error']}")
            file1_info = validation.get("files", {}).get("file1", {})
            file2_info = validation.get("files", {}).get("file2", {})
            is_swapped = (
                file1_info.get("status") == "mismatch" and
                file2_info.get("status") == "mismatch" and
                ("in_namo" in str(namo_file.filename).lower() or "in_remedy" in str(remedy_file.filename).lower())
            )
            return jsonify({
                "error": validation["error"],
                "error_type": "SWAPPED_FILES" if is_swapped else validation["error_type"],
                "files": validation["files"],
                "missing_columns": validation["missing_columns"],
                "internal_error": validation["internal_error"],
                "perf_breakdown": {"file_validation_ms": val_ms},
                "can_auto_swap": is_swapped,
                "namo_slot": file1_info,
                "remedy_slot": file2_info,
            }), 400

        namo_df = validation["namo_df"]
        remedy_df = validation["remedy_df"]
        namo_file_name = validation["namo_file_name"]
        remedy_file_name = validation["remedy_file_name"]

        if namo_df is None or namo_df.empty:
            return jsonify({
                "error": "Dataset 01 (Namo Report) contains no data rows to process.",
                "error_type": "VALIDATION_ERROR",
                "missing_columns": [],
            }), 400

        if remedy_df is None or remedy_df.empty:
            return jsonify({
                "error": "Dataset 02 (Remedy Report) contains no data rows to process.",
                "error_type": "VALIDATION_ERROR",
                "missing_columns": [],
            }), 400

        if validation.get("swapped"):
            nstt_logger.info(
                f"Detected reversed file slots based on column headers: "
                f"using '{namo_file_name}' as Namo Report and '{remedy_file_name}' as Remedy Report."
            )

        # Step 2: VLOOKUP / Left Join on Namo.INCIDENTID = Remedy.INCIDENT_NUMBER
        t_vlookup_start = time.perf_counter()
        try:
            join_result = perform_vlookup(namo_df, remedy_df)
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            internal_err = f"VLOOKUP join exception: {str(exc)}\n{tb}"
            nstt_logger.error(f"[FILE MISMATCH ERROR] {internal_err}")
            return jsonify({
                "error": f"Failed to correlate datasets: {str(exc)}",
                "error_type": "FILE_MISMATCH",
                "internal_error": internal_err,
            }), 400
        t_vlookup_end = time.perf_counter()
        vlookup_ms = round((t_vlookup_end - t_vlookup_start) * 1000, 2)

        if join_result.get("matched_count", 0) == 0 and len(namo_df) > 0 and len(remedy_df) > 0:
            error_msg = (
                f"File Mismatch Error: 0 matching records found between Namo Report ('{namo_file.filename}') "
                f"and Remedy Report ('{remedy_file.filename}'). The Namo INCIDENTID values do not correlate with Remedy INCIDENT_NUMBER."
            )
            sample_namo = list(namo_df["INCIDENTID"].dropna().astype(str).str.strip().head(5))
            sample_remedy = list(remedy_df["INCIDENT_NUMBER"].dropna().astype(str).str.strip().head(5))
            internal_err = (
                f"Zero Match Correlation Failure:\n"
                f"  - Namo File: '{namo_file.filename}' ({len(namo_df)} rows)\n"
                f"  - Remedy File: '{remedy_file.filename}' ({len(remedy_df)} rows)\n"
                f"  - Sample Namo IDs: {sample_namo}\n"
                f"  - Sample Remedy IDs: {sample_remedy}"
            )
            nstt_logger.error(f"[FILE MISMATCH ERROR] {internal_err}")
            return jsonify({
                "error": error_msg,
                "error_type": "FILE_MISMATCH",
                "dataset": "Cross-File Correlation",
                "missing_columns": [],
                "internal_error": internal_err,
            }), 400

        enriched_df = join_result["df"]

        # Step 3: Map INCIDENT_IMPACT (0->SA, 1->NSA) & Check Duplicates
        t_impact_start = time.perf_counter()
        enriched_df = map_incident_impact(enriched_df)
        dup_result = check_duplicates(enriched_df, id_col="INCIDENTID")
        final_df = dup_result["df"]
        t_impact_end = time.perf_counter()
        impact_dup_ms = round((t_impact_end - t_impact_start) * 1000, 2)

        # Step 4: Build Master Response JSON & Remedy Impact Map
        t_master_start = time.perf_counter()
        master_response = build_master_response(final_df)

        remedy_impact_df = map_incident_impact(remedy_df.copy())
        remedy_impact_map = {}
        for _, row in remedy_impact_df.iterrows():
            inc_num = row.get("INCIDENT_NUMBER")
            imp = row.get("INCIDENT_IMPACT")
            if inc_num is not None and not pd.isna(inc_num):
                k = str(inc_num).strip().upper()
                if imp in ("SA", "NSA"):
                    remedy_impact_map[k] = imp
                elif k not in remedy_impact_map:
                    remedy_impact_map[k] = None
        master_response["remedy_impact_map"] = remedy_impact_map
        t_master_end = time.perf_counter()
        master_builder_ms = round((t_master_end - t_master_start) * 1000, 2)

        # Compile processing statistics & warnings
        warnings = []
        if join_result["unmatched_count"] > 0:
            warnings.append(
                f"{join_result['unmatched_count']} Namo incident(s) were not found in Remedy report."
            )

        if dup_result["duplicate_records_count"] > 0:
            warnings.append(
                f"{dup_result['duplicate_records_count']} records flagged as potential duplicate INCIDENTIDs."
            )

        t_upload_now = time.perf_counter()
        upload_total_ms = round((t_upload_now - t_start) * 1000, 2)

        perf_breakdown = {
            "file_validation_ms": val_ms,
            "vlookup_join_ms": vlookup_ms,
            "impact_and_duplicate_ms": impact_dup_ms,
            "master_builder_ms": master_builder_ms,
            "total_upload_ms": upload_total_ms,
        }

        stats = {
            "namo_rows": int(len(namo_df)),
            "remedy_rows": int(len(remedy_df)),
            "matched": int(join_result["matched_count"]),
            "unmatched": int(join_result["unmatched_count"]),
            "duplicates": int(dup_result["duplicate_records_count"]),
            "unique_incident_ids": int(dup_result["unique_incident_ids"]),
            "processing_time_ms": upload_total_ms,
            "perf_breakdown": perf_breakdown,
        }

        # Step 5: Cache the Master Response
        t_cache_start = time.perf_counter()
        upload_id = save_nstt_to_cache(master_response, stats)
        t_cache_end = time.perf_counter()
        cache_store_ms = round((t_cache_end - t_cache_start) * 1000, 2)
        perf_breakdown["cache_store_ms"] = cache_store_ms

        nstt_logger.info(
            f"⏱️ [NSTT PERF COUNTER - UPLOAD COMPLETE]\n"
            f"  ├─ [1. Start / Ingestion & Header Validation]: {val_ms:8.2f} ms ({val_ms / 1000:6.3f} s)\n"
            f"  ├─ [2. VLOOKUP Join (INCIDENTID)]:            {vlookup_ms:8.2f} ms ({vlookup_ms / 1000:6.3f} s)\n"
            f"  ├─ [3. Impact Mapping & Duplicate Check]:     {impact_dup_ms:8.2f} ms ({impact_dup_ms / 1000:6.3f} s)\n"
            f"  ├─ [4. Master Response Construction]:         {master_builder_ms:8.2f} ms ({master_builder_ms / 1000:6.3f} s)\n"
            f"  ├─ [5. Server-side Cache Storage]:            {cache_store_ms:8.2f} ms ({cache_store_ms / 1000:6.3f} s)\n"
            f"  └─ Total Upload Phase Elapsed Time:           {upload_total_ms:8.2f} ms ({upload_total_ms / 1000:6.3f} s)"
        )

        return jsonify({
            "upload_id": upload_id,
            "master_response": master_response,
            "stats": stats,
            "warnings": warnings,
        }), 200

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        nstt_logger.error(f"[NSTT UPLOAD CRITICAL ERROR] {str(exc)}\n{tb}")
        return jsonify({
            "error": f"Upload Processing Error: {str(exc)}",
            "error_type": "SERVER_ERROR",
            "internal_error": tb,
        }), 500


@nstt_bp.route("/master", methods=["GET"], strict_slashes=False)
def get_master_data():
    """
    Retrieves the cached Master Response JSON by upload_id query param (or latest).
    """
    upload_id = request.args.get("upload_id")
    cached = get_nstt_from_cache(upload_id)
    if not cached:
        return jsonify({"error": "No cached NSTT data found. Please upload Namo and Remedy files first."}), 404

    return jsonify({
        "upload_id": cached["upload_id"],
        "master_response": cached["master_response"],
        "stats": cached["stats"],
    }), 200


@nstt_bp.route("/process", methods=["POST"], strict_slashes=False)
def process_nstt():
    """
    Runs the NSTT Rule Engine and Hierarchical Aggregator on a Master Response.

    Accepts JSON body:
      {
        "upload_id": "optional-uuid"   ← uses cached master response
        OR
        "master_response": { ... }     ← direct master response JSON
      }

    Returns:
      {
        "upload_id": "...",
        "classified_master_response": { "records": [...], "classification_stats": {...} },
        "aggregated_result": { ...hierarchical aggregation... },
        "processing_time_ms": 12.3
      }
    """
    t_proc_start = time.perf_counter()

    body: Dict[str, Any] = request.get_json(silent=True) or {}
    upload_id = body.get("upload_id")
    master_response = body.get("master_response")

    # Resolve master_response from cache if not provided inline
    cached = None
    if not master_response:
        cached = get_nstt_from_cache(upload_id)
        if not cached:
            return jsonify({
                "error": "No Master Response found. Provide 'upload_id' or 'master_response' in the request body."
            }), 400
        master_response = cached.get("master_response")
        upload_id = cached.get("upload_id")

    if not master_response or not master_response.get("records"):
        return jsonify({"error": "Master Response is empty or has no records to classify."}), 400

    nstt_logger.info(
        f"Rule Engine processing: upload_id={upload_id}, "
        f"records={master_response.get('total_records', len(master_response.get('records', [])))}"
    )

    try:
        # Step 1: Rule Engine Classification
        t_rules_start = time.perf_counter()
        classified = run_rule_engine(master_response)
        t_rules_end = time.perf_counter()
        rule_engine_ms = round((t_rules_end - t_rules_start) * 1000, 2)

        # Step 2: Hierarchical Matrix Aggregation
        t_agg_start = time.perf_counter()
        records = classified.get("records", [])
        aggregated_result = build_nstt_aggregation(records)
        t_agg_end = time.perf_counter()
        aggregation_ms = round((t_agg_end - t_agg_start) * 1000, 2)
    except Exception as exc:
        nstt_logger.error(f"Rule Engine / Aggregator failed: {str(exc)}", exc_info=True)
        return jsonify({"error": f"Rule Engine / Aggregator processing failed: {str(exc)}"}), 500

    # Step 3: Cache Storage & Final Output Preparation
    t_cache_start = time.perf_counter()
    stats = cached.get("stats", {}) if cached else {}
    upload_ms = stats.get("processing_time_ms") or stats.get("perf_breakdown", {}).get("total_upload_ms", 0.0)

    t_proc_now = time.perf_counter()
    total_proc_ms = round((t_proc_now - t_proc_start) * 1000, 2)
    total_pipeline_ms = round(upload_ms + total_proc_ms, 2)

    proc_perf_breakdown = {
        "rule_engine_ms": rule_engine_ms,
        "aggregation_ms": aggregation_ms,
        "total_process_ms": total_proc_ms,
        "upload_ms": upload_ms,
        "total_pipeline_ms": total_pipeline_ms,
    }
    stats["perf_breakdown"] = {**(stats.get("perf_breakdown") or {}), **proc_perf_breakdown}

    if upload_id:
        save_nstt_to_cache(
            master_response=master_response,
            stats=stats,
            upload_id=upload_id,
            classified_master_response=classified,
            aggregated_result=aggregated_result,
        )
    t_cache_end = time.perf_counter()
    cache_sync_ms = round((t_cache_end - t_cache_start) * 1000, 2)
    proc_perf_breakdown["cache_sync_ms"] = cache_sync_ms

    nstt_logger.info(
        f"⏱️ [NSTT PERF COUNTER - PROCESS & FINAL OUTPUT]\n"
        f"  ├─ [1. Rule Engine Classification]:   {rule_engine_ms:8.2f} ms ({rule_engine_ms / 1000:6.3f} s)\n"
        f"  ├─ [2. Hierarchical Aggregation]:     {aggregation_ms:8.2f} ms ({aggregation_ms / 1000:6.3f} s)\n"
        f"  ├─ [3. Cache Sync & Final Output]:    {cache_sync_ms:8.2f} ms ({cache_sync_ms / 1000:6.3f} s)\n"
        f"  ├─ Process Phase Subtotal:            {total_proc_ms:8.2f} ms ({total_proc_ms / 1000:6.3f} s)\n"
        f"  ├─ Upload Phase Subtotal:             {upload_ms:8.2f} ms ({upload_ms / 1000:6.3f} s)\n"
        f"  └─ Full Pipeline End-to-End:          {total_pipeline_ms:8.2f} ms ({total_pipeline_ms / 1000:6.3f} s)"
    )

    return jsonify({
        "upload_id": upload_id,
        "classified_master_response": classified,
        "aggregated_result": aggregated_result,
        "processing_time_ms": total_proc_ms,
        "perf_breakdown": proc_perf_breakdown,
        "stats": stats,
    }), 200


@nstt_bp.route("/summary", methods=["GET"], strict_slashes=False)
def get_nstt_summary():
    """
    Retrieves the aggregated summary for the current / specified upload.
    """
    upload_id = request.args.get("upload_id")
    cached = get_nstt_from_cache(upload_id)
    if not cached:
        return jsonify({"error": "No cached NSTT data found. Please upload and process files first."}), 404

    aggregated = cached.get("aggregated_result")
    if not aggregated:
        # If not already aggregated, compute from classified_master_response or master_response
        classified = cached.get("classified_master_response")
        if not classified:
            classified = run_rule_engine(cached.get("master_response", {"records": []}))
            cached["classified_master_response"] = classified
        records = classified.get("records", [])
        aggregated = build_nstt_aggregation(records)
        cached["aggregated_result"] = aggregated

    return jsonify({
        "upload_id": cached["upload_id"],
        "aggregated_result": aggregated,
    }), 200


@nstt_bp.route("/drilldown", methods=["POST"], strict_slashes=False)
def get_nstt_drilldown():
    """
    Returns filtered records matching a specific hierarchical category or path.

    Accepts JSON body:
      {
        "category": "automation.same_nstt.im.auto.sa",
        "upload_id": "optional-uuid",
        "records": [ ...optional inline records... ]
      }

    Returns:
      {
        "category": "...",
        "total_records": 100,
        "records": [...]
      }
    """
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    category = body.get("category")
    upload_id = body.get("upload_id")
    records = body.get("records")

    if not category:
        return jsonify({"error": "Missing required field 'category' in request body."}), 400

    if records is None:
        cached = get_nstt_from_cache(upload_id)
        if not cached:
            return jsonify({
                "error": "No cached data found. Provide 'records' inline or specify a valid 'upload_id'."
            }), 400

        classified = cached.get("classified_master_response")
        if classified and classified.get("records"):
            records = classified.get("records")
        else:
            # Classify on the fly if needed
            master_resp = cached.get("master_response", {"records": []})
            classified = run_rule_engine(master_resp)
            cached["classified_master_response"] = classified
            records = classified.get("records", [])

    filtered = filter_records_by_category(records, category)

    return jsonify({
        "category": category,
        "total_records": len(filtered),
        "records": filtered,
    }), 200


@nstt_bp.route("/export", methods=["POST", "GET"], strict_slashes=False)
def export_nstt_excel():
    """
    Generates and streams the styled NSTT Excel report.

    Accepts JSON body or query params:
      {
        "upload_id": "optional-uuid",
        "master_response": { ...optional inline master response... },
        "export_type": "dashboard" | "raw" | "all"
      }

    Returns:
      Streaming attachment of:
        - NSTT_Dashboard_Table_<timestamp>.xlsx (if export_type == "dashboard")
        - NSTT_Raw_Data_VLookup_<timestamp>.xlsx (if export_type == "raw")
        - NSTT_Output_<timestamp>.xlsx (if export_type == "all")
    """
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    upload_id = body.get("upload_id") or request.args.get("upload_id")
    master_response = body.get("master_response")
    export_type = str(
        body.get("export_type")
        or body.get("type")
        or request.args.get("export_type")
        or request.args.get("type")
        or "all"
    ).lower().strip()

    cached = None
    if upload_id:
        cached = get_nstt_from_cache(upload_id)
    if not cached and not master_response:
        cached = get_nstt_from_cache(None)

    if not cached and not master_response:
        return jsonify({
            "error": "No cached data found to export. Provide 'master_response' inline or specify a valid 'upload_id'."
        }), 400

    if cached:
        classified = cached.get("classified_master_response")
        aggregated = cached.get("aggregated_result")
        stats = cached.get("stats", {})
        if not classified:
            master_resp = cached.get("master_response", {"records": []})
            classified = run_rule_engine(master_resp)
        records = classified.get("records", [])
        if not aggregated:
            aggregated = build_nstt_aggregation(records)
    else:
        classified = run_rule_engine(master_response)
        records = classified.get("records", [])
        aggregated = build_nstt_aggregation(records)
        stats = {}

    if not records:
        return jsonify({"error": "No records available for export."}), 400

    timestamp = time.strftime('%Y%m%d_%H%M%S')

    # Instant CSV export path for raw data
    if export_type in ("csv", "raw_csv"):
        try:
            columns = [{"key": h, "label": h} for h in (records[0].keys() if records else [])]
            csv_buffer = generate_csv_export(columns, records)
        except Exception as exc:
            nstt_logger.error(f"CSV generation failed: {str(exc)}", exc_info=True)
            return jsonify({"error": f"Failed to generate CSV export: {str(exc)}"}), 500

        filename = f"NSTT_Raw_Data_VLookup_{timestamp}.csv"
        return send_file(
            csv_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="text/csv",
        )

    try:
        excel_buffer = generate_nstt_excel_workbook(
            master_records=records,
            aggregated_result=aggregated,
            stats=stats,
            export_type=export_type,
        )
    except Exception as exc:
        nstt_logger.error(f"Excel generation failed: {str(exc)}", exc_info=True)
        return jsonify({"error": f"Failed to generate Excel export: {str(exc)}"}), 500

    timestamp = time.strftime('%Y%m%d_%H%M%S')
    if export_type in ("dashboard", "summary"):
        filename = f"NSTT_Dashboard_Table_{timestamp}.xlsx"
    elif export_type in ("raw", "raw_data"):
        filename = f"NSTT_Raw_Data_VLookup_{timestamp}.xlsx"
    else:
        filename = f"NSTT_Output_{timestamp}.xlsx"

    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

