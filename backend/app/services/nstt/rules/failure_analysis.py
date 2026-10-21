"""
Rule: Failure Analysis
========================
Detects failure categories from the Manual NSTT population using CONTAINS checks.

Categories:
  1. "NSTT Number not found in Remedy"
       → is_matched == False (INCIDENTID not in Remedy)

  2. "Ring Failure"
       → DESCRIPTION contains ring-failure keywords:
         "ring fail", "ring failure", "ringfailure", "Ring Collapse" (case/space-insensitive)
         Whole word "ring" (word boundary, case-insensitive)

  3. "Section Failure"
       → DESCRIPTION contains "Section" (case-insensitive)

  4. "Unstitched"
       → AUTOMATION_RCA_CONCLUSION_TEXT contains
         "FLT Observations for Unstitched LSI" (case-insensitive)

  5. "Others"
       → Any Manual NSTT Before SR Creation record that does not match 2, 3, or 4.

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
FAIL_OTHERS = "Others"

# Exact phrase to match for Unstitched (case-insensitive)
_UNSTITCHED_PHRASE = "FLT OBSERVATIONS FOR UNSTITCHED LSI"


def _normalize_for_ring(text: str) -> str:
    """Strips spaces, underscores, and hyphens, then uppercases for ring keyword matching."""
    return re.sub(r"[\s_\-]+", "", text.upper())


def _contains_ring(val: Any) -> bool:
    """
    Returns True if DESCRIPTION contains ring-failure keywords:
      - 'ring fail', 'ring failure', 'ringfailure', 'Ring Collapse' (case/space-insensitive)
      - Whole word 'ring' (word boundary, case-insensitive)
    Avoids false positives on words like 'monitoring', 'sharing', 'spring', 'bearing'.
    """
    if val is None:
        return False
    s = str(val)
    normalized = _normalize_for_ring(s)
    if "RINGFAIL" in normalized or "RINGFAILURE" in normalized or "RINGCOLLAPSE" in normalized:
        return True
    if re.search(r"\bring\b", s, re.IGNORECASE):
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

    Categories:
      - "NSTT Number not found in Remedy": Manual records not found in Remedy (is_matched == False).
      - "Manually tagged – NSTT Before SR Creation" table categories:
          1. Ring Failure
          2. Section Failure
          3. Unstitched
          4. Others (any Before SR Creation records not falling into 1-3)

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        # Only Manual NSTT records are in scope for Failure Analysis
        if not rec.get("is_nstt", False) or rec.get("capture_type") != "Manual":
            rec["failure_category"] = None
            continue

        # Priority 1: Not found in Remedy (Table 1 row 15)
        if not rec.get("is_matched", True):
            rec["failure_category"] = FAIL_NOT_FOUND
            continue

        # For Table 2: Manually tagged – NSTT Before SR Creation
        timing = rec.get("timing_type")
        if timing is not None and timing != "Before SR Creation":
            rec["failure_category"] = None
            continue

        description = rec.get("DESCRIPTION")
        rca_text = rec.get("AUTOMATION_RCA_CONCLUSION_TEXT")

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

        # If it is Before SR Creation and did not match any above category, classify as Others
        if timing == "Before SR Creation":
            rec["failure_category"] = FAIL_OTHERS
        else:
            rec["failure_category"] = None
