"""Frozen harness-side interface (§9.1): `TwinInvocation`, `TwinResult`, `HarnessDriver`.

Contract for driver authors (WP5):

* The driver receives a fully decided invocation. It must NOT widen `tools`
  or `read_roots`; alpha tools are always ("Read", "Grep", "Glob") and MCP is
  always empty.
* `user_text` already contains `<<UNTRUSTED …>>` envelopes for quoted / code
  content; the twin prompt tells the model those carry zero authority.
* Return a `TwinResult`; any failure → raise `DriverError` (the gateway replies
  "暫時無法回應（#seq）" and never guesses).
* `self_check()` returns a list of problems; non-empty → gateway exit 78.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from .. import READ_ONLY_TOOLS


class DriverError(Exception):
    """Driver failed or timed out."""


@dataclass(frozen=True)
class TwinInvocation:
    twin_id: str
    prompt_path: str
    user_text: str                       # already contains UNTRUSTED envelopes
    channel_window: tuple[dict, ...]
    tier: str
    effective_autonomy: str
    tools: tuple[str, ...] = READ_ONLY_TOOLS
    read_roots: tuple[str, ...] = ()
    tainted: bool = False
    predict_first: bool = False
    learner: bool = False                # learner mode: similar cases and counter-examples only, no verdict
    timeout_s: int = 60
    max_budget_usd: float = 0.10
    prompt_sha: str | None = None        # roster promptSha; drivers that read the file re-check it


@dataclass(frozen=True)
class TwinResult:
    reply: str
    citations: tuple[str, ...] = ()
    assumed: tuple[str, ...] = ()
    unverified: tuple[str, ...] = ()
    confidence: Literal["中", "低"] = "低"
    decision_points: tuple[str, ...] = ()
    proposed_actions: tuple[dict, ...] = ()   # alpha: any non-empty → tool_denied, dropped
    suggest_twin: str | None = None           # only *suggests* the human @ another twin
    usage: dict = field(default_factory=dict)  # {"input_tokens","output_tokens","cost_usd"}, optional


# JSON key names a driver's model output uses (§9.1) → TwinResult field names.
RESULT_KEYS = {
    "reply": "reply", "citations": "citations", "assumed": "assumed",
    "unverified": "unverified", "confidence": "confidence",
    "decisionPoints": "decision_points", "proposedActions": "proposed_actions",
    "suggestTwin": "suggest_twin",
}


def result_from_json(obj: dict, usage: dict | None = None) -> TwinResult:
    """Build a TwinResult from the driver JSON contract (camelCase keys)."""
    if not isinstance(obj, dict) or not isinstance(obj.get("reply"), str):
        raise DriverError("driver output is not a TwinResult object")
    kw: dict = {}
    for src, dst in RESULT_KEYS.items():
        if src not in obj or obj[src] is None:
            continue
        val = obj[src]
        if dst in ("citations", "assumed", "unverified", "decision_points"):
            val = tuple(str(v) for v in val) if isinstance(val, list) else ()
        elif dst == "proposed_actions":
            val = tuple(v for v in val if isinstance(v, dict)) if isinstance(val, list) else ()
        elif dst in ("confidence", "suggest_twin", "reply"):
            val = str(val)
        kw[dst] = val
    return TwinResult(usage=dict(usage or {}), **kw)


class HarnessDriver(Protocol):
    name: str                                  # "mock" | "claude-code"

    def self_check(self) -> list[str]: ...     # [] = OK; else gateway exit 78
    def run(self, inv: TwinInvocation) -> TwinResult: ...   # failure → raise DriverError
