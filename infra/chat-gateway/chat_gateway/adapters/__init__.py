"""Chat adapters. Platform SDK adapters (slack, discord; WP4) are imported lazily so
`import chat_gateway.core` never needs a third-party SDK."""
from __future__ import annotations

import importlib

from .base import ChatAdapter

KNOWN = ("mock", "slack", "discord")


def load_adapter_class(name: str) -> type:
    """Return the adapter class for `name` (module `chat_gateway.adapters.<name>`)."""
    if name not in KNOWN:
        raise ValueError(f"unknown adapter {name!r}; choose one of {', '.join(KNOWN)}")
    module = importlib.import_module(f"{__name__}.{name}")
    return getattr(module, f"{name.capitalize()}Adapter")


__all__ = ["ChatAdapter", "KNOWN", "load_adapter_class"]
