"""SQLite — WAL, busy_timeout et verrous applicatifs pour éviter « database is locked »."""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from functools import wraps

from django.core.cache import cache
from django.db import OperationalError
from django.db.backends.signals import connection_created

logger = logging.getLogger(__name__)

_SESSION_LOCK_SECONDS = 90


def setup_sqlite_wal() -> None:
    """Active WAL et busy_timeout sur chaque connexion SQLite."""

    def configure(sender, connection, **kwargs):
        if connection.vendor != "sqlite":
            return
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")

    connection_created.connect(configure, dispatch_uid="ker_sqlite_wal")


def retry_on_db_locked(max_attempts: int = 6, base_delay: float = 0.05):
    """Réessaie les écritures SQLite en cas de contention."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: OperationalError | None = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except OperationalError as exc:
                    if "locked" not in str(exc).lower():
                        raise
                    last_exc = exc
                    delay = base_delay * (2**attempt)
                    logger.debug(
                        "SQLite verrouillé — %s (tentative %s/%s)",
                        func.__name__,
                        attempt + 1,
                        max_attempts,
                    )
                    time.sleep(delay)
            if last_exc:
                raise last_exc
            return None

        return wrapper

    return decorator


@contextmanager
def session_generation_lock(session_id: int, *, wait: bool = True):
    """
    Un seul générateur de question à la fois par session (auto-next + manuel + reconnexion).
    """
    key = f"ker:session-gen:{session_id}"
    acquired = cache.add(key, 1, timeout=_SESSION_LOCK_SECONDS)
    if not acquired and wait:
        deadline = time.monotonic() + 45.0
        while time.monotonic() < deadline:
            if cache.add(key, 1, timeout=_SESSION_LOCK_SECONDS):
                acquired = True
                break
            time.sleep(0.08)
    try:
        yield acquired
    finally:
        if acquired:
            cache.delete(key)
