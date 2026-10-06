"""Harness drivers. Drivers are resolved by name; non-core ones are imported lazily.

`mock` lives here. `claude-code` lives in the sibling `chat_gateway_ext` package (it spawns a
child process, which the hardened core forbids) and is imported only inside `load_driver_class`.
"""
from __future__ import annotations

import importlib

from .base import DriverError, HarnessDriver, TwinInvocation, TwinResult

KNOWN = {
    "mock": ("chat_gateway.drivers.mock", "MockDriver"),
    "claude-code": ("chat_gateway_ext.claude_code", "ClaudeCodeDriver"),
}


def load_driver_class(name: str) -> type:
    if name not in KNOWN:
        raise ValueError(f"unknown driver {name!r}; choose one of {', '.join(KNOWN)}")
    module, cls = KNOWN[name]
    return getattr(importlib.import_module(module), cls)


__all__ = ["DriverError", "HarnessDriver", "TwinInvocation", "TwinResult", "KNOWN", "load_driver_class"]
