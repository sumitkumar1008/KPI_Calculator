"""
Rule: Resolved NSTT Sub-Classification
=========================================
Classifies Resolved NSTT records along 2 axes:
  - factory_type:    IM (FACTORY == "IM") / Non IM (else)
  - allocation_type: Auto (AUTO_ALLOCATION == "yes") / Manual (else)

Only applied to records where nstt_type == "Resolved NSTT".

Resulting hierarchy:
  Resolved NSTT
  ├── IM
  │   ├── Auto
  │   └── Manual
  └── Non IM
      ├── Auto
      └── Manual

Note: Resolved NSTT does NOT sub-classify by SA/NSA — unlike Same NSTT.
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


def apply_resolved_nstt(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'factory_type' and 'allocation_type'
    for Resolved NSTT records.

    Note: factory_type and allocation_type may already be set by same_nstt.
    This function only processes nstt_type == "Resolved NSTT" records.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        if rec.get("nstt_type") != "Resolved NSTT":
            continue

        rec["factory_type"] = _get_factory_type(rec)
        rec["allocation_type"] = _get_allocation_type(rec)
