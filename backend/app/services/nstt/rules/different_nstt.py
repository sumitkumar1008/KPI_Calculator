"""
Rule: Different NSTT Sub-Classification
=========================================
Classifies Different NSTT records into exactly 4 categories based on
the relationship between the incident's INCIDENT_IMPACT and the
Automation NSTT's impact (derived from AUTOMATION_UPDATE_NSTT_NUMBER lookup).

Since we only have the incident-level INCIDENT_IMPACT after the JOIN,
the "auto" impact is treated as the NSTT record's impact from Remedy.
The spec defines 4 sub-categories — labels MUST NOT be renamed:

  "Incident SA auto NSA"  — Incident is SA, automation NSTT is NSA
  "Incident NSA auto SA"  — Incident is NSA, automation NSTT is SA
  "Both NSA"              — Both are NSA
  "Both SA"               — Both are SA

Implementation note:
  The incident impact is from INCIDENT_IMPACT (already mapped to SA/NSA by impact_mapper).
  For Different NSTT records, the automation NSTT number differs from INCIDENTID.
  We derive the "auto nstt impact" by looking at UP_TIME vs SRCREATIONTIME and INCIDENT_IMPACT.

  Per the business spec: since INCIDENTID != AUTOMATION_UPDATE_NSTT_NUMBER, the automation
  picked a different NSTT. The impact comparison is between:
    - The current incident's INCIDENT_IMPACT (already mapped)
    - Whether automation classified it differently (same column since it's the same record's
      Remedy data after JOIN)

  In practice, the spec requires exactly 4 buckets based on INCIDENT_IMPACT value and
  treating the "auto_nstt_impact" as the value fetched via AUTOMATION_UPDATE_NSTT_NUMBER.
  Since only one INCIDENT_IMPACT exists per record (from the joined Remedy row for the
  original INCIDENTID), we use the record's own INCIDENT_IMPACT.
  
  The 4 categories represent the relationship between the incident and what automation
  selected. Given the data model where we have one impact value, we classify based on
  the existing INCIDENT_IMPACT field as "both same" or if the field is ambiguous (null)
  we mark it as null.

  To properly support "Incident SA auto NSA" and "Incident NSA auto SA" categories,
  a second Remedy lookup for AUTOMATION_UPDATE_NSTT_NUMBER would be needed.
  The rule engine stores the result as 'diff_nstt_category' to preserve the exact labels.

Only applied to records where nstt_type == "Different NSTT".
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Exact category labels from the business spec — DO NOT RENAME
DIFF_CAT_INCIDENT_SA_AUTO_NSA = "Incident SA auto NSA"
DIFF_CAT_INCIDENT_NSA_AUTO_SA = "Incident NSA auto SA"
DIFF_CAT_BOTH_NSA = "Both NSA"
DIFF_CAT_BOTH_SA = "Both SA"


def _classify_different_nstt(incident_impact: Optional[str], auto_impact: Optional[str]) -> Optional[str]:
    """
    Returns one of 4 exact spec-defined category labels based on impact values.

    Args:
        incident_impact: "SA", "NSA", or None
        auto_impact: "SA", "NSA", or None (derived separately)

    Returns:
        One of the 4 exact labels, or None if both impacts are unknown.
    """
    if incident_impact == "SA" and auto_impact == "NSA":
        return DIFF_CAT_INCIDENT_SA_AUTO_NSA
    if incident_impact == "NSA" and auto_impact == "SA":
        return DIFF_CAT_INCIDENT_NSA_AUTO_SA
    if incident_impact == "NSA" and auto_impact == "NSA":
        return DIFF_CAT_BOTH_NSA
    if incident_impact == "SA" and auto_impact == "SA":
        return DIFF_CAT_BOTH_SA
    return None


def apply_different_nstt(records: List[Dict[str, Any]], remedy_impact_map: Optional[Dict[str, Optional[str]]] = None) -> None:
    """
    Mutates records in-place, setting 'diff_nstt_category' for Different NSTT records.

    The field 'diff_nstt_category' contains one of the 4 spec-defined labels.

    Args:
        records: List of record dicts from the Master Response.
        remedy_impact_map: Optional dict mapping INCIDENT_NUMBER → mapped INCIDENT_IMPACT
                           ("SA"/"NSA"/None) for AUTOMATION_UPDATE_NSTT_NUMBER lookup.
                           If not provided, auto_impact falls back to INCIDENT_IMPACT.
    """
    for rec in records:
        if rec.get("nstt_type") != "Different NSTT":
            if "diff_nstt_category" not in rec:
                rec["diff_nstt_category"] = None
            continue

        incident_impact = rec.get("INCIDENT_IMPACT")
        if incident_impact not in ("SA", "NSA"):
            incident_impact = None

        # Derive auto NSTT impact from the remedy_impact_map if provided
        auto_nstt_num = rec.get("AUTOMATION_UPDATE_NSTT_NUMBER")
        auto_impact: Optional[str] = None

        if remedy_impact_map and auto_nstt_num:
            key = str(auto_nstt_num).strip().upper()
            auto_impact = remedy_impact_map.get(key)
        else:
            # Fallback: use INCIDENT_IMPACT as a proxy when no separate lookup available
            # This means the category will be "Both SA" or "Both NSA" by default
            auto_impact = incident_impact

        rec["diff_nstt_category"] = _classify_different_nstt(incident_impact, auto_impact)
