"""Backward-compatible facade for the classes service."""

from .classes.commands import (
    create_class,
    create_class_in_transaction,
    update_class,
    update_class_in_transaction,
    delete_class,
    delete_class_in_transaction,
    delete_class_with_unassignment,
    delete_class_with_unassignment_in_transaction,
)
from .classes.queries import (
    get_class_by_id,
    get_class_by_name,
    list_classes,
)

__all__ = [
    "create_class",
    "create_class_in_transaction",
    "update_class",
    "update_class_in_transaction",
    "delete_class",
    "delete_class_in_transaction",
    "delete_class_with_unassignment",
    "delete_class_with_unassignment_in_transaction",
    "get_class_by_id",
    "get_class_by_name",
    "list_classes",
]
