"""
Rule: Automation Classifier
============================
Classifies Automation records into nstt_type — ORDER MATTERS:
  1. SRCREATIONTIME > UP_TIME       → nstt_type = "Resolved NSTT"
  2. INCIDENTID == AUTOMATION_UPDATE_NSTT_NUMBER → nstt_type = "Same NSTT"
  3. Otherwise                      → nstt_type = "Different NSTT"

CRITICAL: The order is specified in the business spec and MUST NOT be changed.
Checking Same before Resolved would produce incorrect classifications.

Only applied to records where capture_type == "Automation".

Date comparison uses robust string-to-datetime parsing with fallback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_datetime_safe(val: Any):
    """Safely parses a date/datetime value into a comparable object. Returns None on failure."""
    if val is None:
        return None
    try:
        import pandas as pd
        parsed = pd.to_datetime(val, dayfirst=False, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed
    except Exception:
        return None


def _is_blank(val: Any) -> bool:
    """Returns True if the value is blank / null / empty."""
    if val is None:
        return True
    return str(val).strip().upper() in ("", "NAN", "NONE", "NULL")


def apply_automation_classifier(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'nstt_type' for Automation records.

    Classification is performed in this strict order:
      1. Resolved NSTT (SRCREATIONTIME > UP_TIME)
      2. Same NSTT (INCIDENTID == AUTOMATION_UPDATE_NSTT_NUMBER)
      3. Different NSTT (fallthrough)

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        if rec.get("capture_type") != "Automation":
            # Don't set nstt_type here — Manual classifier handles Manual records
            if "nstt_type" not in rec:
                rec["nstt_type"] = None
            continue

        srcreationtime = rec.get("SRCREATIONTIME")
        up_time = rec.get("UP_TIME")
        incident_id = rec.get("INCIDENTID")
        auto_nstt_num = rec.get("AUTOMATION_UPDATE_NSTT_NUMBER")

        src_dt = _parse_datetime_safe(srcreationtime)
        up_dt = _parse_datetime_safe(up_time)

        # --- ORDER MATTERS ---

        # Check 1: Resolved NSTT — SRCREATIONTIME > UP_TIME
        if src_dt is not None and up_dt is not None and src_dt > up_dt:
            rec["nstt_type"] = "Resolved NSTT"
            continue

        # Check 2: Same NSTT — INCIDENTID matches AUTOMATION_UPDATE_NSTT_NUMBER
        if (
            not _is_blank(incident_id)
            and not _is_blank(auto_nstt_num)
            and str(incident_id).strip().upper() == str(auto_nstt_num).strip().upper()
        ):
            rec["nstt_type"] = "Same NSTT"
            continue

        # Check 3: Different NSTT — all other Automation records
        rec["nstt_type"] = "Different NSTT"
