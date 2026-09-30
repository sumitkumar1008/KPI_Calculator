"""
NSTT API Routes
===============
Flask Blueprint providing endpoints for NSTT Analytics file ingestion,
VLOOKUP joining, impact conversion, and Master Response generation.
"""

import logging
import sys
import time
from typing import Any, Dict
from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

from app.services.nstt.namo_reader import parse_namo_file
from app.services.nstt.remedy_reader import parse_remedy_file
from app.services.nstt.vlookup import perform_vlookup
from app.services.nstt.impact_mapper import map_incident_impact
from app.services.nstt.duplicate_checker import check_duplicates
from app.services.nstt.master_builder import build_master_response
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
