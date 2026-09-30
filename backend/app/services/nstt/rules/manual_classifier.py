"""
Rule: Manual Classifier
==========================
Classifies Manual capture_type records along 2 axes:
  1. timing_type: Resolved / Before SR Creation / After SR Creation
  2. impact_type: SA / NSA (from INCIDENT_IMPACT)

Timing logic (checked in order):
  Check 1: SRCREATIONTIME > UP_TIME      → timing_type = "Resolved"
  Check 2: SRCREATIONTIME > Submit Date  → timing_type = "Before SR Creation"
  Check 3: SRCREATIONTIME < Submit Date  → timing_type = "After SR Creation"

Then each timing bucket is further split by INCIDENT_IMPACT (SA / NSA).

Only applied to records where capture_type == "Manual".

IMPORTANT: SRCREATIONTIME, UP_TIME, and Submit Date are compared as datetimes.
Missing or unparseable dates result in null timing_type.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_datetime_safe(val: Any):
    """Safely parses a date/datetime value. Returns None on failure."""
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


def _get_impact_type(rec: Dict[str, Any]) -> Optional[str]:
    """Returns mapped INCIDENT_IMPACT ('SA', 'NSA', or None)."""
    impact = rec.get("INCIDENT_IMPACT")
    if impact in ("SA", "NSA"):
        return impact
    return None


def apply_manual_classifier(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'timing_type' and 'impact_type'
    for Manual capture_type records.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        if rec.get("capture_type") != "Manual":
            if "timing_type" not in rec:
                rec["timing_type"] = None
            if "impact_type" not in rec:
                rec["impact_type"] = None
            continue

        srcreationtime = rec.get("SRCREATIONTIME")
        up_time = rec.get("UP_TIME")
        submit_date = rec.get("Submit Date")

        src_dt = _parse_datetime_safe(srcreationtime)
        up_dt = _parse_datetime_safe(up_time)
        submit_dt = _parse_datetime_safe(submit_date)

        timing_type: Optional[str] = None

        # Check 1: SRCREATIONTIME > UP_TIME → "Resolved"
        if src_dt is not None and up_dt is not None and src_dt > up_dt:
            timing_type = "Resolved"

        # Check 2: SRCREATIONTIME > Submit Date → "Before SR Creation"
        elif src_dt is not None and submit_dt is not None and src_dt > submit_dt:
            timing_type = "Before SR Creation"

        # Check 3: SRCREATIONTIME < Submit Date → "After SR Creation"
        elif src_dt is not None and submit_dt is not None and src_dt < submit_dt:
            timing_type = "After SR Creation"

        rec["timing_type"] = timing_type
        rec["impact_type"] = _get_impact_type(rec)
