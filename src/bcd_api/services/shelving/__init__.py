"""Services for shelf-location suggestions."""

from .suggestion import (
    TrainedModel,
    TrainedModelInfo,
    get_status,
    load_current_model,
    suggest,
    train,
)

__all__ = [
    "TrainedModel",
    "TrainedModelInfo",
    "get_status",
    "load_current_model",
    "suggest",
    "train",
]
