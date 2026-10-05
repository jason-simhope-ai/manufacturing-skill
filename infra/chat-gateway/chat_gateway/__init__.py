"""chat_gateway — thin chat-ops gateway for the digital-twin team tier (v0.2.0-alpha).

Stdlib only. The gateway turns chat events into deterministic, audited calls to a
`HarnessDriver`; it never calls a model API itself.

Spec: docs/superpowers/specs/2026-10-05-digital-twin-team-design.md §9, §11.

Exit codes (§18): 0 OK, 3 T3 refused, 64 usage, 65 bad script data, 70 internal, 78 config refused.
"""
from __future__ import annotations

__version__ = "0.2.0-alpha"

EXIT_OK = 0
EXIT_T3 = 3
EXIT_USAGE = 64
EXIT_DATA = 65
EXIT_INTERNAL = 70
EXIT_CONFIG = 78

# Ordered autonomy ladder (§6). Alpha only *runs* the first three.
AUTONOMY = ("observe", "suggest", "draft", "act-with-approval", "act")
ALPHA_MAX_AUTONOMY = "draft"
TIERS = ("T0", "T1", "T2", "T3")
READ_ONLY_TOOLS = ("Read", "Grep", "Glob")


class ConfigRefused(Exception):
    """Raised when the gateway must refuse to start. `exit` is the process exit code."""

    def __init__(self, message: str, exit: int = EXIT_CONFIG):  # noqa: A002 - spec name
        super().__init__(message)
        self.exit = exit


class UsageError(ValueError):
    """A deliberate usage message (unknown adapter or driver name, missing script file). Its text is
    written by this package, so the CLI prints it; any other ValueError prints its class name only."""


def autonomy_rank(level: str) -> int:
    return AUTONOMY.index(level)


def tier_rank(tier: str) -> int:
    return TIERS.index(tier)


def min_autonomy(*levels: str) -> str:
    return min(levels, key=autonomy_rank)
