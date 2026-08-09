"""Inventory Policy - Domain logic for inventory updates and deaccessioning, independent of DB or frameworks."""

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ItemUpdateDecision:
    accepted_updates: dict[str, Any]
    ignored_fields: tuple[str, ...]


def item_update_decision(
    *,
    has_active_loan: bool,
    requested_updates: Mapping[str, Any],
) -> ItemUpdateDecision:
    """Determine which fields of an item can be updated based on its loan status."""
    if has_active_loan:
        accepted = {}
        ignored = []
        for key, value in requested_updates.items():
            if key == "status":
                ignored.append(key)
            else:
                accepted[key] = value
        return ItemUpdateDecision(accepted_updates=accepted, ignored_fields=tuple(ignored))

    return ItemUpdateDecision(accepted_updates=dict(requested_updates), ignored_fields=())


def can_deaccession(*, has_active_loan: bool) -> bool:
    """Retourne True si l'exemplaire peut être supprimé."""
    return not has_active_loan
