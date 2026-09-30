"""
Rule: Capture Type Classification
===================================
Classifies each NSTT record as 'Automation' or 'Manual':
  - AUTOMATION_UPDATE_NSTT_NUMBER is not blank → capture_type = "Automation"
  - Otherwise → capture_type = "Manual"

Only applied to records where is_nstt is True.
"""

from typing import Any, Dict, List


def apply_capture_type(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'capture_type'.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        if not rec.get("is_nstt", False):
            rec["capture_type"] = None
            continue

        auto_nstt = rec.get("AUTOMATION_UPDATE_NSTT_NUMBER")
        if auto_nstt is not None and str(auto_nstt).strip() not in ("", "NAN", "NONE", "NULL"):
            rec["capture_type"] = "Automation"
        else:
            rec["capture_type"] = "Manual"
