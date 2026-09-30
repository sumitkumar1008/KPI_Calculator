"""
NSTT Rule Engine Orchestrator
================================
Processes every record in the Master Response through the complete
NSTT business logic hierarchy in the EXACT prescribed order.

Execution Order (DO NOT CHANGE):
  1. total_sr            — ATTRIBUTEDTO filter → is_total_sr
  2. nstt_count          — blank INCIDENTID filter → is_nstt
  3. capture_type        — Automation vs Manual → capture_type
  4. automation_classifier — Resolved → Same → Different (ORDER MATTERS) → nstt_type
  5. same_nstt           — IM/Non-IM, Auto/Manual, SA/NSA → factory_type, allocation_type, impact_type
  6. different_nstt      — 4 exact sub-categories → diff_nstt_category
  7. resolved_nstt       — IM/Non-IM, Auto/Manual → factory_type, allocation_type
  8. manual_classifier   — Resolved/Before SR/After SR → timing_type, impact_type
  9. wrong_nstt          — CONTAINS-based ANG+TXN exception → exception_type
  10. failure_analysis   — Manual population failure detection → failure_category

Output: classified Master Response with all fields added to each record.

Classification fields added per record:
  is_total_sr:        bool
  is_nstt:            bool
  capture_type:       "Automation" | "Manual" | null
  nstt_type:          "Same NSTT" | "Different NSTT" | "Resolved NSTT" | null
  factory_type:       "IM" | "Non IM" | null
  allocation_type:    "Auto" | "Manual" | null
  impact_type:        "SA" | "NSA" | null
  timing_type:        "Resolved" | "Before SR Creation" | "After SR Creation" | null
  diff_nstt_category: "Incident SA auto NSA" | "Incident NSA auto SA" |
                      "Both NSA" | "Both SA" | null
  exception_type:     "wrong NSTT Attached by automation Ang in TXN Attribution" |
                      "wrong NSTT Attached by Engineer Ang in TXN Attribution" | null
  failure_category:   "NSTT Number not found in Remedy" | "Ring Failure" |
                      "Section Failure" | "Unstitched" | null
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.services.nstt.rules.total_sr import apply_total_sr
from app.services.nstt.rules.nstt_count import apply_nstt_count
from app.services.nstt.rules.capture_type import apply_capture_type
from app.services.nstt.rules.automation_classifier import apply_automation_classifier
from app.services.nstt.rules.same_nstt import apply_same_nstt
from app.services.nstt.rules.different_nstt import apply_different_nstt
from app.services.nstt.rules.resolved_nstt import apply_resolved_nstt
from app.services.nstt.rules.manual_classifier import apply_manual_classifier
from app.services.nstt.rules.wrong_nstt import apply_wrong_nstt
from app.services.nstt.rules.failure_analysis import apply_failure_analysis

logger = logging.getLogger(__name__)


def _build_remedy_impact_map(records: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Builds a lookup map: INCIDENTID (upper) → INCIDENT_IMPACT ("SA"/"NSA"/None).
    Used by the Different NSTT classifier to look up the auto NSTT's impact.
    """
    impact_map: Dict[str, Optional[str]] = {}
    for rec in records:
        inc_id = rec.get("INCIDENTID")
        impact = rec.get("INCIDENT_IMPACT")
        if inc_id:
            key = str(inc_id).strip().upper()
            if impact in ("SA", "NSA"):
                impact_map[key] = impact
            elif key not in impact_map:
                impact_map[key] = None
    return impact_map


def run_rule_engine(master_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs all NSTT classification rules on the Master Response in prescribed order.

    Args:
        master_response: The canonical Master Response dict produced by master_builder.py.
                         Must contain a 'records' list.

    Returns:
        Updated master_response dict with classified records and classification_stats.
    """
    start_time = time.time()

    records: List[Dict[str, Any]] = master_response.get("records", [])
    if not records:
        logger.warning("Rule engine called with empty records list.")
        return {
            **master_response,
            "classification_stats": {
                "total_records": 0,
                "total_sr": 0,
                "nstt_count": 0,
                "automation_count": 0,
                "manual_count": 0,
                "same_nstt": 0,
                "different_nstt": 0,
                "resolved_nstt": 0,
                "wrong_nstt_count": 0,
                "failure_count": 0,
                "processing_time_ms": 0,
            },
        }

    logger.info(f"Rule engine starting: {len(records)} records to classify.")

    # Step 1: Total SR Filter
    apply_total_sr(records)

    # Step 2: NSTT Count
    apply_nstt_count(records)

    # Step 3: Capture Type (Automation vs Manual)
    apply_capture_type(records)

    # Step 4: Automation Classifier (ORDER MATTERS: Resolved → Same → Different)
    apply_automation_classifier(records)

    # Step 5: Same NSTT sub-classification
    apply_same_nstt(records)

    # Step 6: Different NSTT sub-classification (with remedy impact map for proper categorization)
    remedy_impact_map = _build_remedy_impact_map(records)
    apply_different_nstt(records, remedy_impact_map=remedy_impact_map)

    # Step 7: Resolved NSTT sub-classification
    apply_resolved_nstt(records)

    # Step 8: Manual Classifier
    apply_manual_classifier(records)

    # Step 9: Wrong NSTT exception rules
    apply_wrong_nstt(records)

    # Step 10: Failure Analysis (Manual population only)
    apply_failure_analysis(records)

    # Compute classification statistics
    total_sr = sum(1 for r in records if r.get("is_total_sr"))
    nstt_count = sum(1 for r in records if r.get("is_nstt"))
    auto_count = sum(1 for r in records if r.get("capture_type") == "Automation")
    manual_count = sum(1 for r in records if r.get("capture_type") == "Manual")
    same_nstt = sum(1 for r in records if r.get("nstt_type") == "Same NSTT")
    diff_nstt = sum(1 for r in records if r.get("nstt_type") == "Different NSTT")
    resolved_nstt = sum(1 for r in records if r.get("nstt_type") == "Resolved NSTT")
    wrong_nstt = sum(1 for r in records if r.get("exception_type") is not None)
    failures = sum(1 for r in records if r.get("failure_category") is not None)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    logger.info(
        f"Rule engine complete: total_sr={total_sr}, nstt={nstt_count}, "
        f"auto={auto_count}, manual={manual_count}, "
        f"same={same_nstt}, diff={diff_nstt}, resolved={resolved_nstt}, "
        f"wrong_nstt={wrong_nstt}, failures={failures}, time={elapsed_ms}ms"
    )

    classification_stats = {
        "total_records": len(records),
        "total_sr": total_sr,
        "nstt_count": nstt_count,
        "automation_count": auto_count,
        "manual_count": manual_count,
        "same_nstt": same_nstt,
        "different_nstt": diff_nstt,
        "resolved_nstt": resolved_nstt,
        "wrong_nstt_count": wrong_nstt,
        "failure_count": failures,
        "processing_time_ms": elapsed_ms,
    }

    return {
        **master_response,
        "records": records,
        "classification_stats": classification_stats,
    }
