"""
Drill Down Service
==================
Provides 2-level drill-down aggregation logic across summary tables:
- Level 0: Monthly Overview (handled by standard summary services)
- Level 1: Month → 4 Weeks (Week 1: 1-7, Week 2: 8-14, Week 3: 15-21, Week 4: 22-end)
- Level 2: Week → 7 Days Daily Breakdown for that specific week
"""

from datetime import datetime
from typing import Any

from app.services.automation_rca_conclusion import summarize_automation_rca_conclusion
from app.services.automation_run import aggregate_automation_runs, parse_sr_creation_time
from app.services.kpi_aggregator import aggregate_kpi_averages, get_period_bucket
from app.utils.time_utils import parse_datetime


def _extract_month_key(dt: datetime) -> str:
    """Returns YYYY-MM string key for a datetime."""
    return dt.strftime("%Y-%m")


def _is_matching_month(dt: datetime, target_month: str) -> bool:
    """
    Checks if a datetime matches the target month string.
    Matches formats: '2026-08', 'August 2026', 'Aug 2026', '2026-8', etc.
    """
    if not target_month:
        return False
    norm_target = str(target_month).strip().lower()
    
    # Try YYYY-MM match
    month_key = dt.strftime("%Y-%m").lower()
    if month_key == norm_target:
        return True

    # Try Month Year string match (e.g. August 2026)
    full_month = dt.strftime("%B %Y").lower()
    if full_month == norm_target:
        return True

    short_month = dt.strftime("%b %Y").lower()
    if short_month == norm_target:
        return True

    return False


def _get_week_num(dt: datetime) -> int:
    """Month-relative week number: Days 1-7 = 1, Days 8-14 = 2, Days 15-21 = 3, Days 22+ = 4."""
    return min((dt.day - 1) // 7 + 1, 4)


def filter_rows_by_month(rows: list[dict[str, Any]], month_str: str) -> list[dict[str, Any]]:
    """Filters row records belonging to a target month string."""
    filtered = []
    for row in rows:
        dt = parse_sr_creation_time(row.get("SRCREATIONTIME"))
        if dt and _is_matching_month(dt, month_str):
            filtered.append(row)
    return filtered


def filter_rows_by_week(
    rows: list[dict[str, Any]], month_str: str, week_num: int
) -> list[dict[str, Any]]:
    """Filters row records belonging to a target month and week number (1..4)."""
    filtered = []
    for row in rows:
        dt = parse_sr_creation_time(row.get("SRCREATIONTIME"))
        if dt and _is_matching_month(dt, month_str) and _get_week_num(dt) == int(week_num):
            filtered.append(row)
    return filtered


def get_table_drilldown(
    rows: list[dict[str, Any]],
    table_type: str,
    month: str,
    week: int | str | None = None,
) -> dict[str, Any]:
    """
    Main entry point for table drill-down aggregations.
    
    Args:
        rows: List of uploaded/processed row records.
        table_type: One of 'avg', 'automation_run', 'automation_rca'.
        month: Target month string (e.g. '2026-08' or 'August 2026').
        week: Optional week number (1, 2, 3, or 4). If provided, calculates daily breakdown for that week.
        
    Returns:
        dict containing drilldown metadata and aggregated summary array.
    """
    table_type_norm = (table_type or "avg").strip().lower()

    if week is not None and str(week).strip() != "":
        # Level 2: Week -> Daily breakdown for that week's 7 days
        week_int = int(week)
        target_rows = filter_rows_by_week(rows, month, week_int)
        
        if table_type_norm in ("automation_run", "automation_rca_run"):
            result = aggregate_automation_runs(target_rows, group_by="daily")
        elif table_type_norm in ("automation_rca", "automation_rca_conclusion"):
            result = summarize_automation_rca_conclusion(target_rows, group_by="daily")
        else:
            result = aggregate_kpi_averages(target_rows, group_by="daily")

        return {
            "level": "daily",
            "table_type": table_type_norm,
            "month": month,
            "week": week_int,
            "summary": result.get("summary", []),
            "total_records": result.get("total_records", 0),
        }
    else:
        # Level 1: Month -> 4 Weeks breakdown
        target_rows = filter_rows_by_month(rows, month)

        if table_type_norm in ("automation_run", "automation_rca_run"):
            result = aggregate_automation_runs(target_rows, group_by="weekly")
        elif table_type_norm in ("automation_rca", "automation_rca_conclusion"):
            result = summarize_automation_rca_conclusion(target_rows, group_by="weekly")
        else:
            result = aggregate_kpi_averages(target_rows, group_by="weekly")

        return {
            "level": "weekly",
            "table_type": table_type_norm,
            "month": month,
            "week": None,
            "summary": result.get("summary", []),
            "total_records": result.get("total_records", 0),
        }
