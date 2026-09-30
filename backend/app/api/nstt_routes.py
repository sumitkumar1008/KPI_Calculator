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
from flask import Blueprint, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

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


@nstt_bp.route("/health", methods=["GET"])
def nstt_health():
    """Health check endpoint for NSTT module."""
    return jsonify({"status": "healthy", "module": "nstt_analytics"})


@nstt_bp.route("/upload", methods=["POST"])
def upload_nstt_files():
    """
    Ingests Namo and Remedy files, validates columns, executes VLOOKUP join,
    maps INCIDENT_IMPACT, flags duplicates, and constructs the Master Response JSON.
    """
    start_time = time.time()

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
            "error": "Missing required 'namo_file' in form-data. Please attach the Namo Excel/CSV file with key 'namo_file'."
        }), 400

    if not remedy_file:
        return jsonify({
            "error": "Missing required 'remedy_file' in form-data. Please attach the Remedy Excel/CSV file with key 'remedy_file'."
        }), 400

    nstt_logger.info(f"Processing NSTT files: Namo='{namo_file.filename}', Remedy='{remedy_file.filename}'")

    # Step 1: Parse and validate Namo file
    namo_result = parse_namo_file(namo_file, filename=namo_file.filename)
    if not namo_result.get("success"):
        error_msg = namo_result.get("error", "Failed to parse Namo file.")
        nstt_logger.warning(f"Namo validation error: {error_msg}")
        return jsonify({"error": error_msg, "missing_columns": namo_result.get("missing_columns", [])}), 400

    namo_df = namo_result["df"]

    # Step 2: Parse and validate Remedy file
    remedy_result = parse_remedy_file(remedy_file, filename=remedy_file.filename)
    if not remedy_result.get("success"):
        error_msg = remedy_result.get("error", "Failed to parse Remedy file.")
        nstt_logger.warning(f"Remedy validation error: {error_msg}")
        return jsonify({"error": error_msg, "missing_columns": remedy_result.get("missing_columns", [])}), 400

    remedy_df = remedy_result["df"]

    # Step 3: VLOOKUP / Left Join on Namo.INCIDENTID = Remedy.INCIDENT_NUMBER
    try:
        join_result = perform_vlookup(namo_df, remedy_df)
    except Exception as exc:
        nstt_logger.error(f"VLOOKUP join failed: {str(exc)}", exc_info=True)
        return jsonify({"error": f"VLOOKUP join failed: {str(exc)}"}), 500

    enriched_df = join_result["df"]

    # Step 4: Map INCIDENT_IMPACT (0->SA, 1->NSA)
    enriched_df = map_incident_impact(enriched_df)

    # Step 5: Duplicate validation (flag duplicates, never auto-delete)
    dup_result = check_duplicates(enriched_df, id_col="INCIDENTID")
    final_df = dup_result["df"]

    # Step 6: Build Master Response JSON
    master_response = build_master_response(final_df)

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

    stats = {
        "namo_rows": int(len(namo_df)),
        "remedy_rows": int(len(remedy_df)),
        "matched": int(join_result["matched_count"]),
        "unmatched": int(join_result["unmatched_count"]),
        "duplicates": int(dup_result["duplicate_records_count"]),
        "unique_incident_ids": int(dup_result["unique_incident_ids"]),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    # Step 7: Cache the Master Response
    upload_id = save_nstt_to_cache(master_response, stats)

    nstt_logger.info(
        f"NSTT upload success: upload_id={upload_id}, Namo={stats['namo_rows']}, "
        f"Remedy={stats['remedy_rows']}, Matched={stats['matched']}, Time={stats['processing_time_ms']}ms"
    )

    return jsonify({
        "upload_id": upload_id,
        "master_response": master_response,
        "stats": stats,
        "warnings": warnings,
    }), 200


@nstt_bp.route("/master", methods=["GET"])
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


@nstt_bp.route("/process", methods=["POST"])
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
    start_time = time.time()

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
        classified = run_rule_engine(master_response)
        records = classified.get("records", [])
        aggregated_result = build_nstt_aggregation(records)
    except Exception as exc:
        nstt_logger.error(f"Rule Engine / Aggregator failed: {str(exc)}", exc_info=True)
        return jsonify({"error": f"Rule Engine / Aggregator processing failed: {str(exc)}"}), 500

    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    nstt_logger.info(
        f"Rule Engine complete: upload_id={upload_id}, "
        f"total_sr={classified.get('classification_stats', {}).get('total_sr', '?')}, "
        f"nstt={classified.get('classification_stats', {}).get('nstt_count', '?')}, "
        f"time={elapsed_ms}ms"
    )

    # Update cache with classified master response and aggregated result
    stats = cached.get("stats", {}) if cached else {}
    if upload_id:
        save_nstt_to_cache(
            master_response=master_response,
            stats=stats,
            upload_id=upload_id,
            classified_master_response=classified,
            aggregated_result=aggregated_result,
        )

    return jsonify({
        "upload_id": upload_id,
        "classified_master_response": classified,
        "aggregated_result": aggregated_result,
        "processing_time_ms": elapsed_ms,
    }), 200


@nstt_bp.route("/summary", methods=["GET"])
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


@nstt_bp.route("/drilldown", methods=["POST"])
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


@nstt_bp.route("/export", methods=["POST"])
def export_nstt_excel():
    """
    Generates and streams the styled NSTT_Output.xlsx Excel report.

    Accepts JSON body:
      {
        "upload_id": "optional-uuid",
        "master_response": { ...optional inline master response... }
      }

    Returns:
      Streaming attachment of NSTT_Output.xlsx
    """
    body: Dict[str, Any] = request.get_json(silent=True) or {}
    upload_id = body.get("upload_id")
    master_response = body.get("master_response")

    cached = None
    if not master_response:
        cached = get_nstt_from_cache(upload_id)
        if not cached:
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

    try:
        excel_buffer = generate_nstt_excel_workbook(
            master_records=records,
            aggregated_result=aggregated,
            stats=stats,
        )
    except Exception as exc:
        nstt_logger.error(f"Excel generation failed: {str(exc)}", exc_info=True)
        return jsonify({"error": f"Failed to generate Excel export: {str(exc)}"}), 500

    filename = f"NSTT_Output_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        excel_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

