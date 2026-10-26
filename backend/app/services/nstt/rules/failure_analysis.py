"""
Rule: Failure Analysis
========================
Detects failure categories from the Manual NSTT population for Table 2
("Manually tagged – NSTT Before SR Creation") and Table 1 (Row 15: Not found in Remedy).

Categories:
  1. "NSTT Number not found in Remedy"
       → is_matched == False (INCIDENTID not in Remedy)

  2. "Unstitched"
       → In "AUTOMATION_RCA_CONCLUSION_TEXT" of NAMO, if
         "FLT Observations for Unstitched LSI" appears (case/whitespace-flexible,
         singular/plural Observations, or 'Unstitched LSI').

  3. "Ring Failure"
       → In "DESCRIPTION" column of Remedy, if the value contains:
         "ring fail", "ring failure", "ringfailure", "Ring Collapse" (ignore uppercase, spaces etc.)
       EXCLUSION:
         For the ring fail, do NOT count node isolation / node descriptions.
         All descriptions containing "node", "nodes", "node isolation", or "isolated"
         are removed from Ring Failure and inserted into the "Others" category.

  4. "Section Failure"
       → In "DESCRIPTION" column of Remedy, if the value contains "Section" (ignore uppercase, spaces etc.)

  5. "Others"
       → Any Manual NSTT Before SR Creation record that does not match 2, 3, or 4
         (including node / node isolation descriptions).

Only applied to records where capture_type == "Manual" AND is_nstt == True.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
import pandas as pd

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


def _is_node_description(val: Any) -> bool:
    """
    Returns True if DESCRIPTION contains node or node-isolation keywords:
      - 'node', 'nodes' (whole word)
      - 'node isolation', 'isolated', 'isolation'
    These must NEVER be counted in Ring Failure and are moved to 'Others'.
    """
    if val is None:
        return False
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none"):
        return False
    # Check for whole-word node/nodes
    if re.search(r"\bnodes?\b", s, re.IGNORECASE):
        return True
    # Check for isolated / isolation
    if re.search(r"\bisolat(ed|ion)\b", s, re.IGNORECASE):
        return True
    return False


def _contains_ring(val: Any) -> bool:
    """
    Returns True if DESCRIPTION contains ring-failure keywords:
      - 'ring fail', 'ring failure', 'ringfailure', 'Ring Collapse' (case/space-insensitive)
    Does NOT match generic whole-word 'ring' to avoid false positives on node/traffic descriptions.
    """
    if val is None:
        return False
    s = str(val)
    normalized = _normalize_for_ring(s)
    if "RINGFAIL" in normalized or "RINGFAILURE" in normalized or "RINGCOLLAPSE" in normalized:
        return True
    return False


def _contains_section(val: Any) -> bool:
    """Returns True if DESCRIPTION contains 'section' (case-insensitive)."""
    if val is None:
        return False
    return "SECTION" in str(val).upper()


def _get_rca_text(rec: Dict[str, Any]) -> str:
    """
    Extracts AUTOMATION_RCA_CONCLUSION_TEXT from a record,
    checking canonical name and any common aliases or case variations.
    """
    for key in (
        "AUTOMATION_RCA_CONCLUSION_TEXT",
        "AUTOMATION RCA CONCLUSION TEXT",
        "AUTOMATION_RCA_CONCLUSION",
        "RCA_CONCLUSION_TEXT",
        "RCA_CONCLUSION",
        "AUTOMATION_RCA",
    ):
        v = rec.get(key)
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            s = str(v).strip()
            if s and s.lower() not in ("nan", "none"):
                return s

    # Fallback: scan any key containing RCA and CONCLUSION
    for k, v in rec.items():
        if k and "RCA" in str(k).upper() and "CONCLUSION" in str(k).upper():
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                s = str(v).strip()
                if s and s.lower() not in ("nan", "none"):
                    return s

    return ""


def _contains_unstitched(rca_val: Any) -> bool:
    """
    Returns True if AUTOMATION_RCA_CONCLUSION_TEXT contains
    'FLT Observations for Unstitched LSI' (case-insensitive, whitespace-flexible).
    Also supports singular 'Observation' and 'Unstitched LSI'.
    """
    if rca_val is None:
        return False
    s = str(rca_val).strip()
    if not s or s.lower() in ("nan", "none"):
        return False

    # Regex: 'FLT Observations for Unstitched LSI' with flexible whitespace/newlines and optional 's'
    if re.search(r"FLT\s+Observations?\s+for\s+Unstitched\s+LSI", s, re.IGNORECASE):
        return True

    # Normalized whitespace match
    norm = re.sub(r"\s+", " ", s).upper()
    if "FLT OBSERVATIONS FOR UNSTITCHED LSI" in norm or "FLT OBSERVATION FOR UNSTITCHED LSI" in norm:
        return True

    # Unstitched LSI
    if "UNSTITCHED LSI" in norm or "UNSTITCHED" in norm:
        return True

    return False


def apply_failure_analysis(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'failure_category' for Manual NSTT records.

    Categories:
      - "NSTT Number not found in Remedy": Manual records not found in Remedy (is_matched == False).
      - "Manually tagged – NSTT Before SR Creation" table categories:
          1. Unstitched (AUTOMATION_RCA_CONCLUSION_TEXT contains 'FLT Observations for Unstitched LSI')
          2. Node Exclusion → Others (all node / node-isolation descriptions)
          3. Ring Failure (DESCRIPTION contains 'ring fail'/'ring failure'/'Ring Collapse', NOT node)
          4. Section Failure (DESCRIPTION contains 'Section')
          5. Others (all remaining Before SR Creation records)

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
        # Only "Before SR Creation" records get Ring/Section/Unstitched/Others
        timing = rec.get("timing_type")
        if timing != "Before SR Creation":
            rec["failure_category"] = None
            continue

        description = rec.get("DESCRIPTION")
        rca_text = _get_rca_text(rec)

        # Priority 2: Unstitched
        # In "AUTOMATION_RCA_CONCLUSION_TEXT" of NAMO, if "FLT Observations for Unstitched LSI"
        # (also checks DESCRIPTION as fallback if RCA is blank)
        if _contains_unstitched(rca_text) or (not rca_text and _contains_unstitched(description)):
            rec["failure_category"] = FAIL_UNSTITCHED
            continue

        # Priority 3: Node / Node Isolation Exclusion
        # "for the ring fail dont count the node isolation descriptions in this
        #  remove all node description and insert it in other category"
        if _is_node_description(description):
            rec["failure_category"] = FAIL_OTHERS
            continue

        # Priority 4: Ring Failure
        # In "DESCRIPTION" column of Remedy, if the value contains:
        # "ring fail", "ring failure", "ringfailure", "Ring Collapse" (ignore uppercase, spaces etc.)
        if _contains_ring(description):
            rec["failure_category"] = FAIL_RING
            continue

        # Priority 5: Section Failure
        # In "DESCRIPTION" column of Remedy, if the value contains "Section" (ignore uppercase, spaces etc.)
        if _contains_section(description):
            rec["failure_category"] = FAIL_SECTION
            continue

        # Priority 6: All remaining "Before SR Creation" records → Others
        rec["failure_category"] = FAIL_OTHERS

