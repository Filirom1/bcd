"""Holds Policy - Domain logic for reservation logic, independent of DB or frameworks."""

from datetime import date, timedelta
from typing import Optional

_VALID_SOURCES: dict[str, frozenset[str]] = {
    "mark_ready": frozenset({"waiting"}),
    "fulfill": frozenset({"ready"}),
    "cancel": frozenset({"waiting", "ready"}),
}


def hold_expiration_date(today: date, expiration_days: int) -> date:
    """Retourne le dernier jour où une réservation prête est récupérable."""
    return today + timedelta(days=expiration_days)


def is_hold_expired(expiration_date: Optional[date], today: date) -> bool:
    """Une réservation expire strictement après son jour d'expiration."""
    if expiration_date is None:
        return False
    return expiration_date < today


def is_transition_allowed(action: str, status: str) -> bool:
    """Retourne True si la transition est autorisée depuis ce statut."""
    return status in _VALID_SOURCES.get(action, frozenset())
