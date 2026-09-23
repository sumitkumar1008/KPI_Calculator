import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.services.kpi_aggregator import aggregate_kpi_averages
from app.services.automation_run import aggregate_automation_runs
from app.services.automation_rca_conclusion import summarize_automation_rca_conclusion

# Global In-Memory Cache Store
# Stores datasets by upload_id and also holds the 'latest' uploaded dataset.
_CACHE_STORE: Dict[str, Dict[str, Any]] = {}
_LATEST_CACHE_KEY: str = "latest"


def save_to_cache(rows: List[Dict[str, Any]], upload_id: Optional[str] = None) -> str:
    """
    Saves processed KPI rows into the in-memory cache.
    Returns the assigned upload_id.
    """
    uid = upload_id or str(uuid.uuid4())
    cache_record = {
        "upload_id": uid,
        "timestamp": time.time(),
        "row_count": len(rows),
        "rows": rows,
    }
    _CACHE_STORE[uid] = cache_record
    _CACHE_STORE[_LATEST_CACHE_KEY] = cache_record
    return uid


def get_from_cache(upload_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves the cached KPI record for upload_id (or latest if omitted).
    """
    key = upload_id if upload_id and upload_id in _CACHE_STORE else _LATEST_CACHE_KEY
    return _CACHE_STORE.get(key)


def get_cached_export_payload(
    table_type: str = "avg",
    period: str = "monthly",
    upload_id: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], str, str]:
    """
    Prepares columns, data rows, title, and filename from cached data.

    :param table_type: 'avg' | 'automation_run' | 'automation_rca' | 'raw' | 'bucket'
    :param period: 'monthly' | 'weekly' | 'daily'
    :param upload_id: optional cache identifier
    :return: (columns, data, title, filename)
    """
    cached = get_from_cache(upload_id)
    if not cached or not cached.get("rows"):
        raise ValueError("No data found in cache. Please upload a file first.")

    raw_rows = cached["rows"]
    table_type_norm = (table_type or "avg").lower().strip()
    period_norm = (period or "monthly").lower().strip()

    if table_type_norm == "raw":
        columns = [
            {"key": "SRNUMBER", "label": "SR Number"},
            {"key": "SRCREATIONTIME", "label": "Creation Time"},
            {"key": "AUTOMATION_RUN", "label": "Automation Run"},
            {"key": "AUTOMATION_RCA_CONCLUSION", "label": "Automation RCA Conclusion"},
            {"key": "MTTI", "label": "MTTI"},
            {"key": "MTTA", "label": "MTTA"},
            {"key": "MTTAck", "label": "MTTAck"},
            {"key": "MTTR", "label": "MTTR"},
            {"key": "MTTr", "label": "MTTr"},
        ]
        title = "KPI Raw Data Records"
        filename = f"kpi_raw_data_{len(raw_rows)}_records"
        return columns, raw_rows, title, filename

    elif table_type_norm == "automation_run":
        res = aggregate_automation_runs(raw_rows, group_by=period_norm)
        periods = res.get("periods", [])
        columns = [
            {"key": "period_label", "label": "Date / Time"},
            {"key": "total_count", "label": "Total Count"},
            {"key": "Y_count", "label": "Yes"},
            {"key": "N_count", "label": "No"},
            {"key": "Y_percentage", "label": "Yes %"},
            {"key": "N_percentage", "label": "No %"},
        ]
        title = f"Automation Run Summary ({period_norm.upper()})"
        filename = f"automation_run_{period_norm}"
        return columns, periods, title, filename

    elif table_type_norm == "automation_rca":
        res = summarize_automation_rca_conclusion(raw_rows, group_by=period_norm)
        periods = res.get("periods", [])
        columns = [
            {"key": "period_label", "label": "Date / Time"},
            {"key": "total_count", "label": "Total Count"},
            {"key": "Y_count", "label": "Yes"},
            {"key": "N_count", "label": "No"},
            {"key": "Y_percentage", "label": "Yes %"},
            {"key": "N_percentage", "label": "No %"},
        ]
        title = f"Automation RCA Conclusion Summary ({period_norm.upper()})"
        filename = f"automation_rca_conclusion_{period_norm}"
        return columns, periods, title, filename

    elif table_type_norm == "bucket":
        # Incident response distribution buckets
        from app.utils.time_utils import parse_duration_to_seconds

        buckets_def = [
            ("0–15 min", 0, 15 * 60),
            ("15–30 min", 15 * 60, 30 * 60),
            ("30 min–1 hr", 30 * 60, 60 * 60),
            ("1–4 hr", 60 * 60, 4 * 3600),
            ("4–12 hr", 4 * 3600, 12 * 3600),
            ("12 hr+", 12 * 3600, float("inf")),
        ]
        counts = [
            {"bucket": b[0], "MTTI": 0, "MTTR": 0, "MTTr": 0}
            for b in buckets_def
        ]

        for r in raw_rows:
            for kpi in ["MTTI", "MTTR", "MTTr"]:
                sec_val = r.get(f"{kpi}_seconds")
                if sec_val is None:
                    sec_val = parse_duration_to_seconds(r.get(kpi))
                if sec_val is not None and sec_val >= 0:
                    for idx, (label, b_min, b_max) in enumerate(buckets_def):
                        if b_min <= sec_val < b_max:
                            counts[idx][kpi] += 1
                            break

        columns = [
            {"key": "bucket", "label": "Time Bucket"},
            {"key": "MTTI", "label": "MTTI Count"},
            {"key": "MTTR", "label": "MTTR Count"},
            {"key": "MTTr", "label": "MTTr Count"},
        ]
        title = "Incident Response Distribution (KPI Buckets)"
        filename = "kpi_bucket_distribution"
        return columns, counts, title, filename

    else:
        # Default: Unified KPI Averages
        summary_res = aggregate_kpi_averages(raw_rows, group_by=period_norm)
        periods = summary_res.get("summary", [])
        columns = [
            {"key": "period_label", "label": "Time Period"},
            {"key": "AVG_MTTI", "label": "MTTI"},
            {"key": "AVG_MTTA", "label": "MTTA"},
            {"key": "AVG_MTTAck", "label": "MTTAck"},
            {"key": "AVG_MTTR", "label": "MTTR"},
            {"key": "AVG_MTTr", "label": "MTTr"},
        ]
        title = f"Unified KPI Summary ({period_norm.upper()})"
        filename = f"unified_kpi_{period_norm}"
        return columns, periods, title, filename
