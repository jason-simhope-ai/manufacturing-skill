"""Shared plumbing for the SaaS chat adapters (slack, discord). Stdlib only.

NOT exercised against the real platforms in CI; the real adapters need credentials.

* Secrets come only from the environment; refusals name the variable, never its value.
* `max_tier` is T1. Slack may run at T2 only with `MFG_TEAM_SLACK_T2_RISK_ACCEPTED=1`
  AND a valid `riskAcceptance` block in bindings.json (spec §11.1 / §14); Discord never.
* Events reach the adapter through a `transport` (real SDK wrapper, or a test fake):
  `listen(sink)` delivers raw platform dicts to `sink` (None = disconnected),
  `send(kind, payload) -> str`, `identity() -> str` (bot user id), `close()`.
"""
from __future__ import annotations

import datetime as _dt
import os
import queue
import re
import sys
from typing import Any, Iterator, Mapping

from chat_gateway import ConfigRefused
from chat_gateway.adapters.base import ApprovalCard, Event, Reply

PIP_HINT = "pip install -r infra/chat-gateway/requirements-optional.txt"
RISK_FLAG_VAR = "MFG_TEAM_SLACK_T2_RISK_ACCEPTED"
RISK_FIELDS = ("platform", "maxTier", "acceptedBy", "acceptedOn", "expiresOn", "reference")
RISK_MAX_DAYS = 365
APPROVAL_ID_RE = re.compile(r"^apv-[0-9a-f]{4,32}$")
NONCE_RE = re.compile(r"^[0-9a-f]{16,64}$")
DECISIONS = ("approve", "deny")
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def require_env(env: Mapping[str, str], *names: str) -> list[str]:
    """Return the values of `names`; refuse (exit 78) naming only the missing variables."""
    missing = [n for n in names if not env.get(n)]
    if missing:
        raise ConfigRefused("missing required environment variables: " + ", ".join(missing))
    return [env[n] for n in names]


def sdk_missing(adapter: str, module: str) -> ConfigRefused:
    return ConfigRefused(f"the {adapter} adapter needs the optional package '{module}', which is not "
                         f"installed; run: {PIP_HINT}")


def _date(value: object, where: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(str(value))
    except ValueError:
        raise ConfigRefused(f"bindings.riskAcceptance.{where} must be YYYY-MM-DD") from None


def resolve_max_tier(platform: str, bindings: Mapping[str, Any], env: Mapping[str, str],
                     today: _dt.date | None = None) -> str:
    """T1 by default. T2 only for slack, only with the env flag AND a valid, current block."""
    flag = env.get(RISK_FLAG_VAR, "")
    if flag not in ("", "0", "1"):
        raise ConfigRefused(f"{RISK_FLAG_VAR} must be 0 or 1")
    block = bindings.get("riskAcceptance")
    if platform != "slack":
        if block is not None:
            raise ConfigRefused(f"bindings.riskAcceptance is not accepted for {platform}: max tier is T1")
        return "T1"
    if flag != "1":
        return "T1"                       # a block alone never raises the tier
    if not isinstance(block, dict):
        raise ConfigRefused(f"{RISK_FLAG_VAR}=1 but bindings.json has no riskAcceptance block")
    missing = [k for k in RISK_FIELDS if not isinstance(block.get(k), str) or not block[k].strip()]
    if missing:
        raise ConfigRefused("bindings.riskAcceptance missing fields: " + ", ".join(missing))
    if block["platform"] != "slack" or block["maxTier"] != "T2":
        raise ConfigRefused("bindings.riskAcceptance must say platform: slack, maxTier: T2")
    today = today or _dt.date.today()
    start, end = _date(block["acceptedOn"], "acceptedOn"), _date(block["expiresOn"], "expiresOn")
    if not start <= today < end or (end - start).days > RISK_MAX_DAYS:
        raise ConfigRefused(f"bindings.riskAcceptance is not current (valid ≤ {RISK_MAX_DAYS} days)")
    return "T2"


def bound_refs(bindings: Mapping[str, Any], platform: str) -> frozenset[str]:
    chans = bindings.get("channels") if isinstance(bindings, Mapping) else None
    refs = frozenset(str(b["ref"]) for b in (chans or {}).values()
                     if isinstance(b, dict) and b.get("platform") == platform and b.get("ref"))
    if not refs:
        raise ConfigRefused(f"bindings.json binds no {platform} channels; nothing to serve")
    return refs


def attachment_note(names: list[str]) -> str:
    """Attachments are reported by file name only (§11.5); content is never fetched."""
    clean = [_CTRL.sub(" ", n)[:80] for n in names if n][:5]
    return ("\n[附件] " + "、".join(clean)) if clean else ""


def approval_ref(approval_id: str, nonce: str) -> bool:
    return bool(APPROVAL_ID_RE.match(approval_id) and NONCE_RE.match(nonce))


class SaasAdapterBase:
    """Queue-backed `events()` / outbound channel guard shared by slack and discord."""
    name = "?"
    hosting = "saas"
    max_tier = "T1"

    def __init__(self, bindings: Mapping[str, Any], transport: Any, *, env: Mapping[str, str] | None = None):
        env = os.environ if env is None else env
        self.max_tier = resolve_max_tier(self.name, bindings or {}, env)
        self.refs = bound_refs(bindings or {}, self.name)
        self._secrets = require_env(env, *self.SECRET_VARS)  # type: ignore[attr-defined]
        self._transport = transport if transport is not None else self._real_transport()
        self._inbox: queue.Queue = queue.Queue()
        self._bot_id: str | None = None

    def __repr__(self) -> str:                      # never show tokens
        return f"<{type(self).__name__} max_tier={self.max_tier} channels={len(self.refs)}>"

    def _real_transport(self) -> Any:                # pragma: no cover - needs SDK + credentials
        raise NotImplementedError

    @property
    def bot_user_id(self) -> str:
        if self._bot_id is None:
            self._bot_id = str(self._transport.identity())
        return self._bot_id

    def to_event(self, raw: dict) -> Event | None:
        raise NotImplementedError

    def events(self) -> Iterator[Event]:
        self._transport.listen(self._inbox.put)
        while True:
            raw = self._inbox.get()
            if raw is None:
                return
            try:
                ev = self.to_event(raw)
            except (KeyError, TypeError, ValueError, AttributeError):
                print(f"{self.name}: dropped malformed platform event", file=sys.stderr)
                continue
            if ev is not None:
                yield ev

    def _guard(self, channel_ref: str) -> None:
        """Defence in depth: never post anywhere but a bound channel (no DMs, no strays)."""
        if channel_ref not in self.refs:
            raise PermissionError(f"{self.name}: refusing to post to an unbound channel")

    def post(self, reply: Reply) -> str:
        raise NotImplementedError

    def post_approval(self, card: ApprovalCard) -> str:
        raise NotImplementedError

    def close(self) -> None:
        self._inbox.put(None)
        self._transport.close()

