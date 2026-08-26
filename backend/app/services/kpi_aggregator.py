"""
KPI Aggregator Service — Sub-Millisecond Period-Wise Aggregations
===================================================================
Groups calculated incident records by time period (daily, weekly, monthly)
and computes period-wise KPI averages (AVG_MTTI, AVG_MTTA, AVG_MTTAck, AVG_MTTR, AVG_MTTr).

Reuses pre-calculated KPI seconds from API 1 response for sub-millisecond performance.
"""

from datetime import datetime, timedelta
from typing import Any

from app.utils.time_utils import format_timedelta, parse_datetime

# The 5 KPI metrics to aggregate
KPI_KEYS: list[str] = ["MTTI", "MTTA", "MTTAck", "MTTR", "MTTr"]


def get_period_bucket(dt: datetime, group_by: str) -> tuple[str, str, datetime]:
    """
    Computes period key, human-readable label, and sort key datetime for a given datetime.
    
    Supported group_by options:
    - 'daily':  key='YYYY-MM-DD', label='Mon DD, YYYY' (e.g. 'Jul 27, 2026')
    - 'weekly': Month-relative 4 weeks: 'Month YYYY - Week N' (e.g. 'July 2026 - Week 4')
                - Days 1-7:   Week 1
                - Days 8-14:  Week 2
                - Days 15-21: Week 3
                - Days 22-end: Week 4
    - 'monthly': Calendar month: key='YYYY-MM', label='Month YYYY' (e.g. 'July 2026', 'August 2026')
    """
    group_by_norm = group_by.lower().strip()
    
    if group_by_norm == "daily":
        key = dt.strftime("%Y-%m-%d")
        label = dt.strftime("%b %d, %Y")
        sort_dt = datetime(dt.year, dt.month, dt.day)
        return key, label, sort_dt
        
    elif group_by_norm == "weekly":
        # Month-relative 4 weeks
        week_num = min((dt.day - 1) // 7 + 1, 4)
        month_name = dt.strftime("%B")
        key = f"{dt.year}-{dt.month:02d}-W{week_num}"
        label = f"{month_name} {dt.year} - Week {week_num}"
        
        # Sort key: month start + week offset
        start_day_of_week = (week_num - 1) * 7 + 1
        sort_dt = datetime(dt.year, dt.month, start_day_of_week)
        return key, label, sort_dt
        
    else:  # Default to monthly (Calendar Month)
        key = dt.strftime("%Y-%m")
        label = dt.strftime("%B %Y")
        sort_dt = datetime(dt.year, dt.month, 1)
        return key, label, sort_dt



def aggregate_kpi_averages(
    rows: list[dict[str, Any]], group_by: str = "monthly"
) -> dict[str, Any]:
    """
    Aggregates calculated row records by period and computes average KPI durations.
    
    Args:
        rows: List of row dictionaries (output of API 1 or row-level KPI calculations).
        group_by: Granularity string ('daily', 'weekly', 'monthly').
        
    Returns:
        dict containing:
        - group_by: str
        - total_records: int
        - periods_count: int
        - summary: list of period summary objects with AVG_ KPI fields
        - global_warnings: list of string warnings
    """
    valid_group_bys = {"daily", "weekly", "monthly"}
    norm_group_by = group_by.lower().strip() if group_by else "monthly"
    if norm_group_by not in valid_group_bys:
        norm_group_by = "monthly"

    # Bucket structure: period_key -> {"label": str, "sort_dt": datetime, "rows": list}
    buckets: dict[str, dict[str, Any]] = {}
    global_warnings: list[str] = []
    unparsed_date_count = 0

    for row in rows:
        # Extract creation timestamp
        dt = parse_datetime(row.get("SRCREATIONTIME"))
        if dt is None:
            unparsed_date_count += 1
            continue

        key, label, sort_dt = get_period_bucket(dt, norm_group_by)
        if key not in buckets:
            buckets[key] = {
                "period": key,
                "period_label": label,
                "sort_dt": sort_dt,
                "rows": [],
            }
        buckets[key]["rows"].append(row)

    if unparsed_date_count > 0:
        global_warnings.append(
            f"{unparsed_date_count} record(s) omitted from period summary due to missing/invalid SRCREATIONTIME"
        )

    # Sort periods chronologically
    sorted_buckets = sorted(buckets.values(), key=lambda b: b["sort_dt"])
    summary: list[dict[str, Any]] = []

    for bucket in sorted_buckets:
        period_rows = bucket["rows"]
        period_summary: dict[str, Any] = {
            "period": bucket["period"],
            "period_label": bucket["period_label"],
            "record_count": len(period_rows),
        }

        # Calculate average for each of the 5 KPIs
        for kpi in KPI_KEYS:
            avg_key = f"AVG_{kpi}"
            sec_key = f"{kpi}_seconds"
            valid_seconds: list[float] = []

            for r in period_rows:
                # 1. Prefer numeric pre-calculated seconds
                val = r.get(sec_key)
                if val is not None and isinstance(val, (int, float)) and val >= 0:
                    valid_seconds.append(float(val))
                elif kpi in r and r[kpi] is not None:
                    # Fallback string parsing if seconds key is absent
                    try:
                        part = str(r[kpi]).strip()
                        days = 0
                        if "d " in part:
                            d_str, part = part.split("d ", 1)
                            days = int(d_str)
                        parts = [int(p) for p in part.split(":")]
                        if len(parts) == 3:
                            tot_sec = days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]
                            valid_seconds.append(float(tot_sec))
                    except Exception:
                        pass

            if valid_seconds:
                avg_sec = sum(valid_seconds) / len(valid_seconds)
                td = timedelta(seconds=round(avg_sec))
                period_summary[avg_key] = format_timedelta(td)
            else:
                period_summary[avg_key] = None

        summary.append(period_summary)

    return {
        "group_by": norm_group_by,
        "total_records": len(rows),
        "periods_count": len(summary),
        "summary": summary,
        "global_warnings": global_warnings,
    }
