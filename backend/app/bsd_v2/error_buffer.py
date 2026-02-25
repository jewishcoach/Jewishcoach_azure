# -*- coding: utf-8 -*-
"""In-memory buffer of recent BSD V2 errors for debugging."""

import logging
from collections import deque
from datetime import datetime
from typing import List, Dict, Any

_MAX_ERRORS = 20
_errors: deque = deque(maxlen=_MAX_ERRORS)


def capture_error(tag: str, error: Exception, extra: Dict[str, Any] = None) -> None:
    """Append error to buffer."""
    try:
        _errors.append({
            "tag": tag,
            "message": str(error),
            "type": type(error).__name__,
            "extra": extra or {},
            "ts": datetime.utcnow().isoformat() + "Z",
        })
    except Exception:
        pass


def get_recent_errors() -> List[Dict[str, Any]]:
    """Return recent errors (newest first)."""
    return list(reversed(_errors))
