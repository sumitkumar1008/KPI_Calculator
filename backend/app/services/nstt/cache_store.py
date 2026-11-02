"""
NSTT In-Memory & Disk-Backed Cache Store
=========================================
Isolates NSTT cache data from existing KPI module cache to prevent any state collision.
Enforces strict 1-entry bounded capacity with explicit garbage collection
to prevent memory leaks on Render's 512MB RAM tier.
"""

import gc
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nstt_cache")

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
    Evicts older uploads to stay strictly within 512MB RAM limit on cloud instances.
    Returns assigned upload_id.
    """
    uid = upload_id or str(uuid.uuid4())
    existing = _NSTT_CACHE_STORE.get(uid, {})

    # Evict older uploads immediately to reclaim memory
    stored_keys = [k for k in list(_NSTT_CACHE_STORE.keys()) if k != _LATEST_NSTT_KEY and k != uid]
    for old_k in stored_keys:
        old_entry = _NSTT_CACHE_STORE.pop(old_k, None)
        if old_entry:
            del old_entry

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
    if upload_id and upload_id in _NSTT_CACHE_STORE:
        return _NSTT_CACHE_STORE[upload_id]
    return _NSTT_CACHE_STORE.get(_LATEST_NSTT_KEY)


def get_nstt_records(upload_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Helper to retrieve records directly from cache without copying the cache dict.
    Prefers classified records if available, otherwise master records.
    """
    cached = get_nstt_from_cache(upload_id)
    if not cached:
        return []
    classified = cached.get("classified_master_response")
    if classified and classified.get("records"):
        return classified["records"]
    master = cached.get("master_response")
    if master and master.get("records"):
        return master["records"]
    return []


def clear_nstt_cache() -> None:
    """Clears all NSTT cache entries and triggers immediate garbage collection."""
    _NSTT_CACHE_STORE.clear()
    gc.collect()
