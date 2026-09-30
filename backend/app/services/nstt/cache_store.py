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
) -> str:
    """
    Saves NSTT Master Response and processing stats in cache.
    Returns assigned upload_id.
    """
    uid = upload_id or str(uuid.uuid4())
    cache_record = {
        "upload_id": uid,
        "timestamp": time.time(),
        "total_records": master_response.get("total_records", 0),
        "master_response": master_response,
        "stats": stats,
    }
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
