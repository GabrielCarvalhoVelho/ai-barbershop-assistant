"""
Account lockout em memória com TTL.

Regras:
  - MAX_ATTEMPTS falhas consecutivas -> bloqueio por LOCKOUT_DURATION_SECONDS
  - Chave de lockout: phone (não expõe se user existe — previne enumeration)
  - TTL limpo lazily em is_locked (sem background task)
"""

import time
from threading import Lock

MAX_ATTEMPTS: int = 5
LOCKOUT_DURATION_SECONDS: int = 900  # 15 minutos

# { phone: {"attempts": int, "locked_until": float | None} }
_store: dict[str, dict] = {}
_lock = Lock()


def is_locked(phone: str) -> bool:
    with _lock:
        entry = _store.get(phone)
        if not entry:
            return False
        locked_until = entry.get("locked_until")
        if locked_until and time.monotonic() < locked_until:
            return True
        if locked_until:
            del _store[phone]
        return False


def record_failure(phone: str) -> None:
    with _lock:
        entry = _store.setdefault(phone, {"attempts": 0, "locked_until": None})
        entry["attempts"] += 1
        if entry["attempts"] >= MAX_ATTEMPTS:
            entry["locked_until"] = time.monotonic() + LOCKOUT_DURATION_SECONDS


def reset_attempts(phone: str) -> None:
    with _lock:
        _store.pop(phone, None)


def get_lockout_remaining(phone: str) -> int:
    with _lock:
        entry = _store.get(phone)
        if not entry or not entry.get("locked_until"):
            return 0
        return max(0, int(entry["locked_until"] - time.monotonic()))
