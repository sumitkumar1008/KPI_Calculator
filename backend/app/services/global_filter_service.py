"""
Global Filter Service
=====================
Provides centralized management for global filters applied across KPI aggregations.
Supports period filtering ('daily', 'weekly', 'monthly') and extensibility for future filters.
"""

from typing import Any, Dict, List

# Allowed time period values for global filtering
ALLOWED_PERIODS: set[str] = {"daily", "weekly", "monthly"}

DEFAULT_FILTER_STATE: Dict[str, Any] = {
    "period": "daily",
    "search": "",
    "date_range": None,
}


def validate_and_normalize_filters(raw_filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Validates and normalizes incoming global filter parameters.
    
    Args:
        raw_filters: Dictionary containing filter parameters.
        
    Returns:
        Normalized filter dictionary with default fallbacks.
    """
    filters = dict(DEFAULT_FILTER_STATE)
    if not raw_filters or not isinstance(raw_filters, dict):
        return filters

    period = str(raw_filters.get("period", "daily")).lower().strip()
    if period in ALLOWED_PERIODS:
        filters["period"] = period
    else:
        filters["period"] = "daily"

    if "search" in raw_filters and isinstance(raw_filters["search"], str):
        filters["search"] = raw_filters["search"].strip()

    if "date_range" in raw_filters:
        filters["date_range"] = raw_filters["date_range"]

    return filters


def get_available_filter_options() -> Dict[str, Any]:
    """
    Returns available filter configurations and metadata for the frontend.
    Allows frontend to dynamically render available filter options.
    """
    return {
        "periods": [
            {"value": "daily", "label": "Daily"},
            {"value": "weekly", "label": "Weekly"},
            {"value": "monthly", "label": "Monthly"},
        ],
        "default_period": "daily",
        "extensible_fields": ["period", "date_range", "search"],
    }
