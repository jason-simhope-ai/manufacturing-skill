"""Chat adapters. `mock` lives here. The SaaS adapters (slack, discord) cross the network boundary,
so they live in the sibling `chat_gateway_ext` package and are imported only inside
`load_adapter_class`; `import chat_gateway.core` never needs a third-party SDK."""
from __future__ import annotations

import importlib

from .base import ChatAdapter

KNOWN = {
    "mock": ("chat_gateway.adapters.mock", "MockAdapter"),
    "slack": ("chat_gateway_ext.slack", "SlackAdapter"),
    "discord": ("chat_gateway_ext.discord", "DiscordAdapter"),
}


def load_adapter_class(name: str) -> type:
    """Return the adapter class for `name` (absolute module path from KNOWN)."""
    if name not in KNOWN:
        raise ValueError(f"unknown adapter {name!r}; choose one of {', '.join(KNOWN)}")
    module, cls = KNOWN[name]
    return getattr(importlib.import_module(module), cls)


__all__ = ["ChatAdapter", "KNOWN", "load_adapter_class"]
