"""
Rule: Same NSTT Sub-Classification
=====================================
Classifies Same NSTT records along 3 axes:
  - factory_type:    IM (FACTORY == "IM") / Non IM (else)
  - allocation_type: Auto (AUTO_ALLOCATION == "yes") / Manual (else)
  - impact_type:     SA / NSA / null (from already-mapped INCIDENT_IMPACT)

Only applied to records where nstt_type == "Same NSTT".

Resulting hierarchy:
  Same NSTT
  ├── IM
  │   ├── Auto → SA / NSA
  │   └── Manual → SA / NSA
  └── Non IM
      ├── Auto → SA / NSA
      └── Manual → SA / NSA

Comparisons:
  - FACTORY == "IM" is STRICT EQUALITY (case-insensitive strip)
  - AUTO_ALLOCATION == "yes" is STRICT EQUALITY (case-insensitive strip)
  - INCIDENT_IMPACT is already mapped to "SA" / "NSA" / None by impact_mapper.py
"""

from __future__ import annotations

from typing import Any, Dict, List


def _get_factory_type(rec: Dict[str, Any]) -> str:
    """Returns 'IM' if FACTORY equals 'IM' (case-insensitive), else 'Non IM'."""
    factory = rec.get("FACTORY")
    if factory is not None and str(factory).strip().upper() == "IM":
        return "IM"
    return "Non IM"


def _get_allocation_type(rec: Dict[str, Any]) -> str:
    """Returns 'Auto' if AUTO_ALLOCATION equals 'yes' (case-insensitive), else 'Manual'."""
    auto_alloc = rec.get("AUTO_ALLOCATION")
    if auto_alloc is not None and str(auto_alloc).strip().lower() == "yes":
        return "Auto"
    return "Manual"


def _get_impact_type(rec: Dict[str, Any]) -> "str | None":
    """Returns the already-mapped INCIDENT_IMPACT ('SA', 'NSA', or None)."""
    impact = rec.get("INCIDENT_IMPACT")
    if impact in ("SA", "NSA"):
        return impact
    return None


def apply_same_nstt(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'factory_type', 'allocation_type', 'impact_type'
    for Same NSTT records.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        if rec.get("nstt_type") != "Same NSTT":
            # Set defaults for non-applicable records
            if "factory_type" not in rec:
                rec["factory_type"] = None
            if "allocation_type" not in rec:
                rec["allocation_type"] = None
            if "impact_type" not in rec:
                rec["impact_type"] = None
            continue

        rec["factory_type"] = _get_factory_type(rec)
        rec["allocation_type"] = _get_allocation_type(rec)
        rec["impact_type"] = _get_impact_type(rec)
