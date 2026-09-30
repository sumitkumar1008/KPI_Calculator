"""
NSTT Hierarchical Aggregation Engine
====================================
Aggregates classified Master Response records into the hierarchical data model
matching SampleOutput.xlsx structure and powers the UI Summary Table,
Failure Analysis table, and Drill-down queries.

Hierarchical Structure:
  Total SR
  └── NSTT Count (%)
      ├── Automation (%)
      │   ├── Same NSTT (%)
      │   │   ├── IM (%)
      │   │   │   ├── Auto (SA / NSA)
      │   │   │   └── Manual (SA / NSA)
      │   │   └── Non IM (%)
      │   │       ├── Auto (SA / NSA)
      │   │       └── Manual (SA / NSA)
      │   ├── Different NSTT (%)
      │   │   ├── Incident SA auto NSA
      │   │   ├── Incident NSA auto SA
      │   │   ├── Both NSA
      │   │   └── Both SA
      │   └── Resolved NSTT (%)
      │       ├── IM (Auto / Manual)
      │       └── Non IM (Auto / Manual)
      └── Manual (%)
          ├── Resolved (SA / NSA)
          ├── Before SR Creation (SA / NSA)
          └── After SR Creation (SA / NSA)

Wrong NSTT Exceptions:
  - Automation ANG in TXN
  - Engineer ANG in TXN

Failure Analysis:
  - NSTT Number not found in Remedy
  - Ring Failure
  - Section Failure
  - Unstitched
  - Grand Total
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Exact exception type strings from Phase 2
WRONG_NSTT_AUTO = "wrong NSTT Attached by automation Ang in TXN Attribution"
WRONG_NSTT_ENG = "wrong NSTT Attached by Engineer Ang in TXN Attribution"

# Exact failure category strings from Phase 2
FAIL_NOT_FOUND = "NSTT Number not found in Remedy"
FAIL_RING = "Ring Failure"
FAIL_SECTION = "Section Failure"
FAIL_UNSTITCHED = "Unstitched"

# Exact Different NSTT category strings from Phase 2
DIFF_INC_SA_AUTO_NSA = "Incident SA auto NSA"
DIFF_INC_NSA_AUTO_SA = "Incident NSA auto SA"
DIFF_BOTH_NSA = "Both NSA"
DIFF_BOTH_SA = "Both SA"


def _calc_percentage(numerator: int, denominator: int) -> float:
    """Calculates percentage rounded to 2 decimal places, safe against zero-division."""
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def build_nstt_aggregation(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes complete hierarchical aggregation from classified records.

    Args:
        records: List of record dictionaries after running the NSTT Rule Engine.

    Returns:
        Hierarchical dictionary matching SampleOutput.xlsx structure.
    """
    if not records:
        return _empty_aggregation()

    total_sr = 0
    nstt_count = 0

    # Automation counters
    auto_count = 0

    # Same NSTT
    same_im_auto_sa = 0
    same_im_auto_nsa = 0
    same_im_man_sa = 0
    same_im_man_nsa = 0

    same_non_im_auto_sa = 0
    same_non_im_auto_nsa = 0
    same_non_im_man_sa = 0
    same_non_im_man_nsa = 0

    # Different NSTT
    diff_inc_sa_auto_nsa = 0
    diff_inc_nsa_auto_sa = 0
    diff_both_nsa = 0
    diff_both_sa = 0

    # Resolved NSTT (Automation)
    resolved_im_auto = 0
    resolved_im_manual = 0
    resolved_non_im_auto = 0
    resolved_non_im_manual = 0

    # Manual counters
    manual_count = 0
    man_res_sa = 0
    man_res_nsa = 0
    man_before_sa = 0
    man_before_nsa = 0
    man_after_sa = 0
    man_after_nsa = 0

    # Wrong NSTT
    wrong_auto = 0
    wrong_eng = 0

    # Failures
    fail_not_found = 0
    fail_ring = 0
    fail_section = 0
    fail_unstitched = 0

    for r in records:
        is_sr = bool(r.get("is_total_sr"))
        if is_sr:
            total_sr += 1

        is_n = bool(r.get("is_nstt"))
        if is_n:
            nstt_count += 1

        cap_type = r.get("capture_type")
        nstt_type = r.get("nstt_type")
        factory_type = r.get("factory_type")
        alloc_type = r.get("allocation_type")
        impact_type = r.get("impact_type")
        timing_type = r.get("timing_type")
        diff_cat = r.get("diff_nstt_category")
        exc_type = r.get("exception_type")
        fail_cat = r.get("failure_category")

        # Wrong NSTT Exceptions
        if exc_type == WRONG_NSTT_AUTO:
            wrong_auto += 1
        elif exc_type == WRONG_NSTT_ENG:
            wrong_eng += 1

        # Failure Analysis
        if fail_cat == FAIL_NOT_FOUND:
            fail_not_found += 1
        elif fail_cat == FAIL_RING:
            fail_ring += 1
        elif fail_cat == FAIL_SECTION:
            fail_section += 1
        elif fail_cat == FAIL_UNSTITCHED:
            fail_unstitched += 1

        # Only process hierarchy if is_nstt is True
        if not is_n:
            continue

        if cap_type == "Automation":
            auto_count += 1

            if nstt_type == "Same NSTT":
                if factory_type == "IM":
                    if alloc_type == "Auto":
                        if impact_type == "SA":
                            same_im_auto_sa += 1
                        elif impact_type == "NSA":
                            same_im_auto_nsa += 1
                    elif alloc_type == "Manual":
                        if impact_type == "SA":
                            same_im_man_sa += 1
                        elif impact_type == "NSA":
                            same_im_man_nsa += 1
                elif factory_type == "Non IM":
                    if alloc_type == "Auto":
                        if impact_type == "SA":
                            same_non_im_auto_sa += 1
                        elif impact_type == "NSA":
                            same_non_im_auto_nsa += 1
                    elif alloc_type == "Manual":
                        if impact_type == "SA":
                            same_non_im_man_sa += 1
                        elif impact_type == "NSA":
                            same_non_im_man_nsa += 1

            elif nstt_type == "Different NSTT":
                if diff_cat == DIFF_INC_SA_AUTO_NSA:
                    diff_inc_sa_auto_nsa += 1
                elif diff_cat == DIFF_INC_NSA_AUTO_SA:
                    diff_inc_nsa_auto_sa += 1
                elif diff_cat == DIFF_BOTH_NSA:
                    diff_both_nsa += 1
                elif diff_cat == DIFF_BOTH_SA:
                    diff_both_sa += 1

            elif nstt_type == "Resolved NSTT":
                if factory_type == "IM":
                    if alloc_type == "Auto":
                        resolved_im_auto += 1
                    elif alloc_type == "Manual":
                        resolved_im_manual += 1
                elif factory_type == "Non IM":
                    if alloc_type == "Auto":
                        resolved_non_im_auto += 1
                    elif alloc_type == "Manual":
                        resolved_non_im_manual += 1

        elif cap_type == "Manual":
            manual_count += 1

            if timing_type == "Resolved":
                if impact_type == "SA":
                    man_res_sa += 1
                elif impact_type == "NSA":
                    man_res_nsa += 1
            elif timing_type == "Before SR Creation":
                if impact_type == "SA":
                    man_before_sa += 1
                elif impact_type == "NSA":
                    man_before_nsa += 1
            elif timing_type == "After SR Creation":
                if impact_type == "SA":
                    man_after_sa += 1
                elif impact_type == "NSA":
                    man_after_nsa += 1

    # Aggregate Same NSTT IM & Non-IM subtotals
    same_im_auto_total = same_im_auto_sa + same_im_auto_nsa
    same_im_man_total = same_im_man_sa + same_im_man_nsa
    same_im_total = same_im_auto_total + same_im_man_total

    same_non_im_auto_total = same_non_im_auto_sa + same_non_im_auto_nsa
    same_non_im_man_total = same_non_im_man_sa + same_non_im_man_nsa
    same_non_im_total = same_non_im_auto_total + same_non_im_man_total

    same_nstt_total = same_im_total + same_non_im_total

    # Aggregate Different NSTT subtotals
    diff_nstt_total = diff_inc_sa_auto_nsa + diff_inc_nsa_auto_sa + diff_both_nsa + diff_both_sa

    # Aggregate Resolved NSTT subtotals
    resolved_im_total = resolved_im_auto + resolved_im_manual
    resolved_non_im_total = resolved_non_im_auto + resolved_non_im_manual
    resolved_nstt_total = resolved_im_total + resolved_non_im_total

    # Manual subtotals
    man_res_total = man_res_sa + man_res_nsa
    man_before_total = man_before_sa + man_before_nsa
    man_after_total = man_after_sa + man_after_nsa

    # Failures grand total
    fail_grand_total = fail_not_found + fail_ring + fail_section + fail_unstitched

    # Percentages with total_sr as the base denominator
    nstt_pct = _calc_percentage(nstt_count, total_sr)
    auto_pct = _calc_percentage(auto_count, total_sr)
    manual_pct = _calc_percentage(manual_count, total_sr)

    same_nstt_pct = _calc_percentage(same_nstt_total, total_sr)
    same_im_pct = _calc_percentage(same_im_total, total_sr)
    same_non_im_pct = _calc_percentage(same_non_im_total, total_sr)

    diff_nstt_pct = _calc_percentage(diff_nstt_total, total_sr)
    resolved_nstt_pct = _calc_percentage(resolved_nstt_total, total_sr)

    man_res_pct = _calc_percentage(man_res_total, total_sr)
    man_before_pct = _calc_percentage(man_before_total, total_sr)
    man_after_pct = _calc_percentage(man_after_total, total_sr)

    return {
        "total_sr": total_sr,
        "nstt_count": nstt_count,
        "nstt_percentage": nstt_pct,

        "automation": {
            "count": auto_count,
            "percentage": auto_pct,

            "same_nstt": {
                "count": same_nstt_total,
                "percentage": same_nstt_pct,
                "im": {
                    "count": same_im_total,
                    "percentage": same_im_pct,
                    "auto": {
                        "count": same_im_auto_total,
                        "sa": same_im_auto_sa,
                        "nsa": same_im_auto_nsa,
                    },
                    "manual": {
                        "count": same_im_man_total,
                        "sa": same_im_man_sa,
                        "nsa": same_im_man_nsa,
                    },
                },
                "non_im": {
                    "count": same_non_im_total,
                    "percentage": same_non_im_pct,
                    "auto": {
                        "count": same_non_im_auto_total,
                        "sa": same_non_im_auto_sa,
                        "nsa": same_non_im_auto_nsa,
                    },
                    "manual": {
                        "count": same_non_im_man_total,
                        "sa": same_non_im_man_sa,
                        "nsa": same_non_im_man_nsa,
                    },
                },
            },

            "different_nstt": {
                "count": diff_nstt_total,
                "percentage": diff_nstt_pct,
                "incident_sa_auto_nsa": diff_inc_sa_auto_nsa,
                "incident_nsa_auto_sa": diff_inc_nsa_auto_sa,
                "both_nsa": diff_both_nsa,
                "both_sa": diff_both_sa,
            },

            "resolved_nstt": {
                "count": resolved_nstt_total,
                "percentage": resolved_nstt_pct,
                "im": {
                    "count": resolved_im_total,
                    "auto": resolved_im_auto,
                    "manual": resolved_im_manual,
                },
                "non_im": {
                    "count": resolved_non_im_total,
                    "auto": resolved_non_im_auto,
                    "manual": resolved_non_im_manual,
                },
            },
        },

        "manual": {
            "count": manual_count,
            "percentage": manual_pct,
            "resolved": {
                "count": man_res_total,
                "percentage": man_res_pct,
                "sa": man_res_sa,
                "nsa": man_res_nsa,
            },
            "before_sr_creation": {
                "count": man_before_total,
                "percentage": man_before_pct,
                "sa": man_before_sa,
                "nsa": man_before_nsa,
            },
            "after_sr_creation": {
                "count": man_after_total,
                "percentage": man_after_pct,
                "sa": man_after_sa,
                "nsa": man_after_nsa,
            },
        },

        "wrong_nstt": {
            "automation_ang_txn": wrong_auto,
            "engineer_ang_txn": wrong_eng,
        },

        "failures": {
            "nstt_not_found": fail_not_found,
            "ring_failure": fail_ring,
            "section_failure": fail_section,
            "unstitched": fail_unstitched,
            "grand_total": fail_grand_total,
        },
    }



def _empty_aggregation() -> Dict[str, Any]:
    """Returns a zeroed-out hierarchical structure."""
    return {
        "total_sr": 0,
        "nstt_count": 0,
        "nstt_percentage": 0.0,
        "automation": {
            "count": 0,
            "percentage": 0.0,
            "same_nstt": {
                "count": 0,
                "percentage": 0.0,
                "im": {
                    "count": 0,
                    "percentage": 0.0,
                    "auto": {"count": 0, "sa": 0, "nsa": 0},
                    "manual": {"count": 0, "sa": 0, "nsa": 0},
                },
                "non_im": {
                    "count": 0,
                    "percentage": 0.0,
                    "auto": {"count": 0, "sa": 0, "nsa": 0},
                    "manual": {"count": 0, "sa": 0, "nsa": 0},
                },
            },
            "different_nstt": {
                "count": 0,
                "percentage": 0.0,
                "incident_sa_auto_nsa": 0,
                "incident_nsa_auto_sa": 0,
                "both_nsa": 0,
                "both_sa": 0,
            },
            "resolved_nstt": {
                "count": 0,
                "percentage": 0.0,
                "im": {"count": 0, "auto": 0, "manual": 0},
                "non_im": {"count": 0, "auto": 0, "manual": 0},
            },
        },
        "manual": {
            "count": 0,
            "percentage": 0.0,
            "resolved": {"count": 0, "sa": 0, "nsa": 0},
            "before_sr_creation": {"count": 0, "sa": 0, "nsa": 0},
            "after_sr_creation": {"count": 0, "sa": 0, "nsa": 0},
        },
        "wrong_nstt": {
            "automation_ang_txn": 0,
            "engineer_ang_txn": 0,
        },
        "failures": {
            "nstt_not_found": 0,
            "ring_failure": 0,
            "section_failure": 0,
            "unstitched": 0,
            "grand_total": 0,
        },
    }


# ==============================================================================
# DRILL-DOWN FILTER LOGIC
# ==============================================================================

_DRILLDOWN_PREDICATES: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    # Top level
    "total_sr": lambda r: bool(r.get("is_total_sr")),
    "nstt": lambda r: bool(r.get("is_nstt")),
    "nstt_count": lambda r: bool(r.get("is_nstt")),

    # Automation
    "automation": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation",

    # Same NSTT
    "automation.same_nstt": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT",
    "same_nstt": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT",

    # Same NSTT -> IM
    "automation.same_nstt.im": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM",
    "automation.same_nstt.im.auto": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Auto",
    "automation.same_nstt.im.auto.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Auto" and r.get("impact_type") == "SA",
    "automation.same_nstt.im.auto.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Auto" and r.get("impact_type") == "NSA",

    "automation.same_nstt.im.manual": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Manual",
    "automation.same_nstt.im.manual.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Manual" and r.get("impact_type") == "SA",
    "automation.same_nstt.im.manual.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Manual" and r.get("impact_type") == "NSA",

    # Same NSTT -> Non IM
    "automation.same_nstt.non_im": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM",
    "automation.same_nstt.non_im.auto": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Auto",
    "automation.same_nstt.non_im.auto.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Auto" and r.get("impact_type") == "SA",
    "automation.same_nstt.non_im.auto.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Auto" and r.get("impact_type") == "NSA",

    "automation.same_nstt.non_im.manual": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Manual",
    "automation.same_nstt.non_im.manual.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Manual" and r.get("impact_type") == "SA",
    "automation.same_nstt.non_im.manual.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Same NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Manual" and r.get("impact_type") == "NSA",

    # Different NSTT
    "automation.different_nstt": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Different NSTT",
    "different_nstt": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Different NSTT",
    "automation.different_nstt.incident_sa_auto_nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Different NSTT" and r.get("diff_nstt_category") == DIFF_INC_SA_AUTO_NSA,
    "automation.different_nstt.incident_nsa_auto_sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Different NSTT" and r.get("diff_nstt_category") == DIFF_INC_NSA_AUTO_SA,
    "automation.different_nstt.both_nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Different NSTT" and r.get("diff_nstt_category") == DIFF_BOTH_NSA,
    "automation.different_nstt.both_sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Different NSTT" and r.get("diff_nstt_category") == DIFF_BOTH_SA,

    # Resolved NSTT (Automation)
    "automation.resolved_nstt": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT",
    "resolved_nstt": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT",
    "automation.resolved_nstt.im": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT" and r.get("factory_type") == "IM",
    "automation.resolved_nstt.im.auto": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Auto",
    "automation.resolved_nstt.im.manual": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT" and r.get("factory_type") == "IM" and r.get("allocation_type") == "Manual",
    "automation.resolved_nstt.non_im": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT" and r.get("factory_type") == "Non IM",
    "automation.resolved_nstt.non_im.auto": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Auto",
    "automation.resolved_nstt.non_im.manual": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Automation" and r.get("nstt_type") == "Resolved NSTT" and r.get("factory_type") == "Non IM" and r.get("allocation_type") == "Manual",

    # Manual
    "manual": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual",
    "manual.resolved": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "Resolved",
    "manual.resolved.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "Resolved" and r.get("impact_type") == "SA",
    "manual.resolved.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "Resolved" and r.get("impact_type") == "NSA",

    "manual.before_sr_creation": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "Before SR Creation",
    "manual.before_sr_creation.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "Before SR Creation" and r.get("impact_type") == "SA",
    "manual.before_sr_creation.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "Before SR Creation" and r.get("impact_type") == "NSA",

    "manual.after_sr_creation": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "After SR Creation",
    "manual.after_sr_creation.sa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "After SR Creation" and r.get("impact_type") == "SA",
    "manual.after_sr_creation.nsa": lambda r: bool(r.get("is_nstt")) and r.get("capture_type") == "Manual" and r.get("timing_type") == "After SR Creation" and r.get("impact_type") == "NSA",

    # Wrong NSTT
    "wrong_nstt": lambda r: r.get("exception_type") is not None,
    "wrong_nstt.automation_ang_txn": lambda r: r.get("exception_type") == WRONG_NSTT_AUTO,
    "wrong_nstt.engineer_ang_txn": lambda r: r.get("exception_type") == WRONG_NSTT_ENG,

    # Failures
    "failures": lambda r: r.get("failure_category") is not None,
    "failures.grand_total": lambda r: r.get("failure_category") is not None,
    "failures.nstt_not_found": lambda r: r.get("failure_category") == FAIL_NOT_FOUND,
    "failures.ring_failure": lambda r: r.get("failure_category") == FAIL_RING,
    "failures.section_failure": lambda r: r.get("failure_category") == FAIL_SECTION,
    "failures.unstitched": lambda r: r.get("failure_category") == FAIL_UNSTITCHED,
}


def filter_records_by_category(records: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    """
    Filters classified records based on a hierarchical category key or path.

    Args:
        records: List of classified record dictionaries.
        category: Dot-notation or path string (e.g. 'automation.same_nstt.im.auto.sa').

    Returns:
        List of matching record dictionaries.
    """
    if not records or not category:
        return []

    clean_cat = str(category).strip().lower()

    # Direct predicate lookup
    if clean_cat in _DRILLDOWN_PREDICATES:
        predicate = _DRILLDOWN_PREDICATES[clean_cat]
        return [r for r in records if predicate(r)]

    # Dynamic fallback: check if clean_cat matches any specific label or custom path
    # Try normalizing separators (slashes -> dots)
    dot_cat = clean_cat.replace("/", ".").replace(" ", "_")
    if dot_cat in _DRILLDOWN_PREDICATES:
        predicate = _DRILLDOWN_PREDICATES[dot_cat]
        return [r for r in records if predicate(r)]

    # Fallback to general field matches
    logger.warning(f"Unrecognized drilldown category: '{category}'. Returning empty match list.")
    return []
