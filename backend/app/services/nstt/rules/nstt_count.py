"""
Rule: NSTT Count Filter
========================
From Total SR records, sets is_nstt = True where INCIDENTID is not blank.

Only applied to records where is_total_sr is True.
"""

from typing import Any, Dict, List


def apply_nstt_count(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'is_nstt' flag.
    Only Total SR records with a non-blank INCIDENTID qualify.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        if not rec.get("is_total_sr", False):
            rec["is_nstt"] = False
            continue

        incident_id = rec.get("INCIDENTID")
        if incident_id is not None and str(incident_id).strip() not in ("", "NAN", "NONE", "NULL"):
            rec["is_nstt"] = True
        else:
            rec["is_nstt"] = False
