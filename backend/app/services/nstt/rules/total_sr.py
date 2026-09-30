"""
Rule: Total SR Filter
======================
Sets is_total_sr = True on records where ATTRIBUTEDTO is one of:
  TNL, TXN, TXN_Infra, TXN_Hardware

All comparisons are case-insensitive and whitespace-stripped.
"""

from typing import Any, Dict, List

TOTAL_SR_VALUES = {"TNL", "TXN", "TXN_INFRA", "TXN_HARDWARE"}


def apply_total_sr(records: List[Dict[str, Any]]) -> None:
    """
    Mutates records in-place, setting 'is_total_sr' flag.

    Args:
        records: List of record dicts from the Master Response.
    """
    for rec in records:
        attributed_to = rec.get("ATTRIBUTEDTO")
        if attributed_to is not None:
            normalized = str(attributed_to).strip().upper()
            rec["is_total_sr"] = normalized in TOTAL_SR_VALUES
        else:
            rec["is_total_sr"] = False
