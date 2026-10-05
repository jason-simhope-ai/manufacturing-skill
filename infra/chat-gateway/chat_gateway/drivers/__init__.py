"""Harness drivers. `claude_code` (WP5) is imported lazily."""
from __future__ import annotations

import importlib

from .base import DriverError, HarnessDriver, TwinInvocation, TwinResult

KNOWN = {"mock": ("mock", "MockDriver"), "claude-code": ("claude_code", "ClaudeCodeDriver")}


def load_driver_class(name: str) -> type:
    if name not in KNOWN:
        raise ValueError(f"unknown driver {name!r}; choose one of {', '.join(KNOWN)}")
    module, cls = KNOWN[name]
    return getattr(importlib.import_module(f"{__name__}.{module}"), cls)


__all__ = ["DriverError", "HarnessDriver", "TwinInvocation", "TwinResult", "KNOWN", "load_driver_class"]
