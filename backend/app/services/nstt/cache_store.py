"""
NSTT In-Memory Cache Store
==========================
Isolates NSTT cache data from existing KPI module cache to prevent any state collision.
"""

import time
import uuid
from typing import Any, Dict, List, Optional

_NSTT_CACHE_STORE: Dict[str, Dict[str, Any]] = {}
_LATEST_NSTT_KEY: str = "latest_nstt"


def save_nstt_to_cache(
    master_response: Dict[str, Any],
    stats: Dict[str, Any],
    upload_id: Optional[str] = None,
    classified_master_response: Optional[Dict[str, Any]] = None,
    aggregated_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Saves NSTT Master Response, classified data, aggregation, and stats in cache.
    Returns assigned upload_id.
    """
    uid = upload_id or str(uuid.uuid4())
    existing = _NSTT_CACHE_STORE.get(uid, {})
    
    cache_record = {
        **existing,
        "upload_id": uid,
        "timestamp": time.time(),
        "total_records": master_response.get("total_records", len(master_response.get("records", []))),
        "master_response": master_response,
        "stats": stats,
    }
    if classified_master_response is not None:
        cache_record["classified_master_response"] = classified_master_response
    if aggregated_result is not None:
        cache_record["aggregated_result"] = aggregated_result

    _NSTT_CACHE_STORE[uid] = cache_record
    _NSTT_CACHE_STORE[_LATEST_NSTT_KEY] = cache_record
    return uid


def get_nstt_from_cache(upload_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieves cached NSTT data by upload_id (or latest if omitted).
    """
    key = upload_id if upload_id and upload_id in _NSTT_CACHE_STORE else _LATEST_NSTT_KEY
    return _NSTT_CACHE_STORE.get(key)


def clear_nstt_cache() -> None:
    """Clears all NSTT cache entries (useful for testing)."""
    _NSTT_CACHE_STORE.clear()
