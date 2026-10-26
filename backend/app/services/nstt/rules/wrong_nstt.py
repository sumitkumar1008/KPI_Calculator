"""
Rule: Wrong NSTT Exception Rules
===================================
Detects records where the wrong NSTT was attached using CONTAINS checks (NOT equality).

Conditions (BOTH must be true):
  ASSIGNED_SUPPORT_COMPANY contains "ANG"  (case-insensitive, substring)
  AND ATTRIBUTEDTO contains "TXN"          (case-insensitive, substring)

Based on capture_type:
  Automation → exception_type = "wrong NSTT Attached by automation Ang in TXN Attribution"
  Manual     → exception_type = "wrong NSTT Attached by Engineer Ang in TXN Attribution"

CRITICAL: This rule uses CONTAINS (substring), NOT equality matching.
See Critical Implementation Rule 1 in the spec.

Only applied to records where is_nstt is True.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Exact label strings from the business spec — DO NOT RENAME
WRONG_NSTT_AUTOMATION = "wrong NSTT Attached by automation Ang in TXN Attribution"
WRONG_NSTT_ENGINEER = "wrong NSTT Attached by Engineer Ang in TXN Attribution"


def _contains_ang(val: Any) -> bool:
    """Returns True if value contains 'ANG' (case-insensitive)."""
    if val is None:
        return False
    return "ANG" in str(val).strip().upper()


def _contains_txn(val: Any) -> bool:
    """Returns True if value contains 'TXN' (case-insensitive)."""
    if val is None:
        return False
    return "TXN" in str(val).strip().upper()


def apply_wrong_nstt(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'exception_type' for records matching
    the Wrong NSTT condition.

    CONTAINS check on both ASSIGNED_SUPPORT_COMPANY and ATTRIBUTEDTO:
      ASSIGNED_SUPPORT_COMPANY contains "ANG" (case-insensitive)
      AND ATTRIBUTEDTO contains "TXN" (case-insensitive)

    Automation records matching this condition receive:
      exception_type = "wrong NSTT Attached by automation Ang in TXN Attribution"

    Business Rule:
      For records with Auto Capture Same NSTT and Wrong NSTT Attached, any Incident ID
      that lies in both cases is removed from the Same NSTT bifurcation.

    Args:
        records: List of record dicts from the Master Response.
    """
    wrong_auto_incident_ids = set()

    for rec in records:
        if not rec.get("is_nstt", False):
            rec["exception_type"] = None
            continue

        assigned_support = rec.get("ASSIGNED_SUPPORT_COMPANY")
        attributed_to = rec.get("ATTRIBUTEDTO")

        # Both CONTAINS conditions must be true
        if _contains_ang(assigned_support) and _contains_txn(attributed_to):
            capture_type = rec.get("capture_type")
            if capture_type == "Automation":
                rec["exception_type"] = WRONG_NSTT_AUTOMATION
                inc_id = rec.get("INCIDENTID")
                if inc_id is not None:
                    wrong_auto_incident_ids.add(str(inc_id).strip().upper())
            elif capture_type == "Manual":
                rec["exception_type"] = WRONG_NSTT_ENGINEER
            else:
                rec["exception_type"] = None
        else:
            rec["exception_type"] = None

    # Business Rule:
    # "for the auto capture same nstt and wrong nstt attached the incident id that lies in both case
    #  remove from the same nstt bifurcation"
    for rec in records:
        if rec.get("capture_type") == "Automation" and rec.get("nstt_type") == "Same NSTT":
            inc_id = str(rec.get("INCIDENTID") or "").strip().upper()
            if rec.get("exception_type") == WRONG_NSTT_AUTOMATION or inc_id in wrong_auto_incident_ids:
                rec["nstt_type"] = None
                rec["factory_type"] = None
                rec["allocation_type"] = None

