"""
Rule: Failure Analysis
========================
Detects failure categories from the Manual NSTT population using CONTAINS checks.

Categories (mutually exclusive, first match wins):
  1. "NSTT Number not found in Remedy"
       → is_matched == False (INCIDENTID not in Remedy)

  2. "Ring Failure"
       → DESCRIPTION contains ring-failure keywords (case/space-insensitive)
         Keywords: "RING", "RING FAILURE", "RING_FAILURE"

  3. "Section Failure"
       → DESCRIPTION contains "Section" (case-insensitive)

  4. "Unstitched"
       → AUTOMATION_RCA_CONCLUSION_TEXT contains
         "FLT Observations for Unstitched LSI" (case-insensitive)

Only applied to records where capture_type == "Manual" AND is_nstt == True.
CONTAINS matching — NOT equality.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Exact category labels from the business spec — DO NOT RENAME
FAIL_NOT_FOUND = "NSTT Number not found in Remedy"
FAIL_RING = "Ring Failure"
FAIL_SECTION = "Section Failure"
FAIL_UNSTITCHED = "Unstitched"

# Ring failure keywords — normalized (no spaces/underscores)
_RING_KEYWORDS = {"RING", "RINGFAILURE"}

# Exact phrase to match for Unstitched (case-insensitive)
_UNSTITCHED_PHRASE = "FLT OBSERVATIONS FOR UNSTITCHED LSI"


def _normalize_for_ring(text: str) -> str:
    """Strips spaces and underscores, then uppercases for ring keyword matching."""
    return re.sub(r"[\s_]+", "", text.upper())


def _contains_ring(val: Any) -> bool:
    """Returns True if DESCRIPTION contains any ring-failure keyword (space/case insensitive)."""
    if val is None:
        return False
    normalized = _normalize_for_ring(str(val))
    for kw in _RING_KEYWORDS:
        if kw in normalized:
            return True
    return False


def _contains_section(val: Any) -> bool:
    """Returns True if DESCRIPTION contains 'section' (case-insensitive)."""
    if val is None:
        return False
    return "SECTION" in str(val).upper()


def _contains_unstitched(val: Any) -> bool:
    """
    Returns True if AUTOMATION_RCA_CONCLUSION_TEXT contains
    'FLT Observations for Unstitched LSI' (case-insensitive).
    """
    if val is None:
        return False
    return _UNSTITCHED_PHRASE in str(val).strip().upper()


def apply_failure_analysis(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'failure_category' for Manual NSTT records.

    Categories are checked in priority order:
      1. NSTT not found in Remedy (is_matched == False)
      2. Ring Failure (DESCRIPTION contains ring terms)
      3. Section Failure (DESCRIPTION contains "Section")
      4. Unstitched (AUTOMATION_RCA_CONCLUSION_TEXT contains the phrase)

    Records not matching any category get failure_category = None.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        # Only Manual NSTT records are in scope for Failure Analysis
        if not rec.get("is_nstt", False) or rec.get("capture_type") != "Manual":
            rec["failure_category"] = None
            continue

        description = rec.get("DESCRIPTION")
        rca_text = rec.get("AUTOMATION_RCA_CONCLUSION_TEXT")
        is_matched = rec.get("is_matched", True)

        # Priority 1: Not found in Remedy
        if not is_matched:
            rec["failure_category"] = FAIL_NOT_FOUND
            continue

        # Priority 2: Ring Failure
        if _contains_ring(description):
            rec["failure_category"] = FAIL_RING
            continue

        # Priority 3: Section Failure
        if _contains_section(description):
            rec["failure_category"] = FAIL_SECTION
            continue

        # Priority 4: Unstitched
        if _contains_unstitched(rca_text):
            rec["failure_category"] = FAIL_UNSTITCHED
            continue

        # No failure category matched
        rec["failure_category"] = None
