"""
automation_rca_conclusion.py

Service to count, per time period (daily / weekly / monthly),
how many records had AUTOMATION_RCA_CONCLUSION answered as Y vs N,
grouped by SRCREATIONTIME.

Drop this file into: backend/app/services/automation_rca_conclusion.py
"""

from typing import Any

from app.services.automation_run import parse_sr_creation_time
from app.services.kpi_aggregator import get_period_bucket

YES_VALUES = {"1", "true", "t", "y", "yes", "on"}


def _is_yes(value: Any) -> bool:
    """Return True if the raw field value counts as 'Y'/Yes."""
    if value is None:
        return False
    return str(value).strip().lower() in YES_VALUES


def summarize_automation_rca_conclusion(
    records: list[dict[str, Any]], group_by: str = "daily"
) -> dict[str, Any]:
    """
    Group records by time period and count Y/N for AUTOMATION_RCA_CONCLUSION.

    Returns:
        {
            "group_by": "monthly",
            "total_records": 15,
            "periods_count": 1,
            "omitted_records": 0,
            "summary": [
                {
                    "period": "2026-08",
                    "period_label": "August 2026",
                    "Y_count": 10,
                    "N_count": 5,
                    "total_count": 15
                }
            ]
        }
    """
    buckets: dict[str, dict[str, Any]] = {}
    omitted_count = 0

    for record in records:
        dt = parse_sr_creation_time(record.get("SRCREATIONTIME"))
        if dt is None:
            omitted_count += 1
            continue

        period, period_label, sort_datetime = get_period_bucket(dt, group_by)
        if period not in buckets:
            buckets[period] = {
                "period": period,
                "period_label": period_label,
                "sort_datetime": sort_datetime,
                "Y_count": 0,
                "N_count": 0,
            }

        if _is_yes(record.get("AUTOMATION_RCA_CONCLUSION")):
            buckets[period]["Y_count"] += 1
        else:
            buckets[period]["N_count"] += 1

    summary = []
    for bucket in sorted(buckets.values(), key=lambda b: b["sort_datetime"]):
        summary.append({
            "period": bucket["period"],
            "period_label": bucket["period_label"],
            "Y_count": bucket["Y_count"],
            "N_count": bucket["N_count"],
            "total_count": bucket["Y_count"] + bucket["N_count"],
        })

    return {
        "group_by": group_by,
        "total_records": len(records),
        "periods_count": len(summary),
        "summary": summary,
        "omitted_records": omitted_count,
    }