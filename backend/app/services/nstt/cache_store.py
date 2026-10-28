"""
NSTT In-Memory Cache Store
==========================
Isolates NSTT cache data from existing KPI module cache to prevent any state collision.
"""

import gc
import time
import uuid
from typing import Any, Dict, List, Optional

_NSTT_CACHE_STORE: Dict[str, Dict[str, Any]] = {}
_LATEST_NSTT_KEY: str = "latest_nstt"
_MAX_NSTT_CACHE_ENTRIES: int = 1


def save_nstt_to_cache(
    master_response: Dict[str, Any],
    stats: Dict[str, Any],
    upload_id: Optional[str] = None,
    classified_master_response: Optional[Dict[str, Any]] = None,
    aggregated_result: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Saves NSTT Master Response, classified data, aggregation, and stats in cache.
    Evicts older uploads to stay within 512MB RAM limit on cloud instances.
    Returns assigned upload_id.
    """
    uid = upload_id or str(uuid.uuid4())
    existing = _NSTT_CACHE_STORE.get(uid, {})

    # Evict older uploads
    stored_keys = [k for k in list(_NSTT_CACHE_STORE.keys()) if k != _LATEST_NSTT_KEY and k != uid]
    if len(stored_keys) >= _MAX_NSTT_CACHE_ENTRIES:
        for old_k in stored_keys[: len(stored_keys) - _MAX_NSTT_CACHE_ENTRIES + 1]:
            _NSTT_CACHE_STORE.pop(old_k, None)

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
    gc.collect()
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
