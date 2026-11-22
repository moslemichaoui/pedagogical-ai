"""A tiny in-process rate limiter.

A single-teacher deployment does not need Redis, but it does need a guard
against a retry loop burning the Gemini quota. The window is per process and
per client address; that is deliberate and documented.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Callable, Deque, Dict, Tuple

from flask import current_app, jsonify, request

_LOCK = threading.Lock()
_HITS: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def _client_key() -> str:
    """Key the rolling window on the peer address.

    ``X-Forwarded-For`` is client-controlled unless the request actually came
    from a configured proxy, so trusting it blindly lets anyone reset their
    quota by spoofing a new address on every request.
    """
    peer = request.remote_addr or "local"
    trusted = {
        item.strip()
        for item in str(current_app.config.get("TRUSTED_PROXIES", "") or "").split(",")
        if item.strip()
    }
    if peer in trusted:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return peer


def rate_limit(bucket: str, config_key: str) -> Callable:
    """Decorate a view with a rolling one-hour limit from app config."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args, **kwargs):
            limit = int(current_app.config.get(config_key, 0) or 0)
            if limit <= 0 or current_app.config.get("TESTING"):
                return view(*args, **kwargs)

            key = (bucket, _client_key())
            now = time.monotonic()
            with _LOCK:
                hits = _HITS[key]
                while hits and now - hits[0] > 3600:
                    hits.popleft()
                if len(hits) >= limit:
                    retry_after = int(3600 - (now - hits[0])) + 1
                    response = jsonify(
                        {
                            "success": False,
                            "error": "تم بلوغ الحد الأقصى للطلبات. أعد المحاولة لاحقاً.",
                            "code": "rate_limited",
                        }
                    )
                    response.status_code = 429
                    response.headers["Retry-After"] = str(retry_after)
                    return response
                hits.append(now)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def reset_limits() -> None:
    """Testing helper."""
    with _LOCK:
        _HITS.clear()
