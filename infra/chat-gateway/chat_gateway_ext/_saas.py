"""Shared plumbing for the SaaS chat adapters (slack, discord). Stdlib only.

NOT exercised against the real platforms in CI; the real adapters need credentials.

* Secrets come only from the environment; refusals name the variable, never its value.
* `max_tier` is T1 for every SaaS adapter, hard (spec §11.1; T2 on SaaS is deferred, §14).
* Events reach the adapter through a `transport` (real SDK wrapper, or a test fake):
  `listen(sink)` delivers raw platform dicts to `sink` (None = disconnected),
  `send(kind, payload) -> str`, `identity() -> str` (bot user id), `close()`.
  The Slack transport also has `granted_scopes() -> list[str] | None` (the bot token's scopes).
"""
from __future__ import annotations

import os
import queue
import re
import sys
import threading
from typing import Any, Iterator, Mapping

from chat_gateway import ConfigRefused
from chat_gateway.adapters.base import ApprovalCard, Event, Reply

PIP_HINT = "pip install -r infra/chat-gateway/requirements-optional.txt"
# Always used with fullmatch: `$` alone also matches before a trailing newline (EXT-09).
APPROVAL_ID_RE = re.compile(r"apv-[0-9a-f]{4,32}")
NONCE_RE = re.compile(r"[0-9a-f]{16,64}")
DECISIONS = ("approve", "deny")
# EXT-12: at most this many platform events wait in the inbox. The gateway handles one event at
# a time (each may run a model call), so a burst beyond this is dropped, counted and audited by
# the gateway as `overflow` rather than queued without bound.
INBOX_MAX = 256
# C0, DEL, C1 (incl. U+0085 NEL) and U+2028/U+2029: anything `str.splitlines()` breaks on, so a
# file name can never push text out of its `[附件]` line (EXT-10).
_CTRL = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def require_env(env: Mapping[str, str], *names: str) -> list[str]:
    """Return the values of `names`; refuse (exit 78) naming only the missing variables."""
    missing = [n for n in names if not env.get(n)]
    if missing:
        raise ConfigRefused("missing required environment variables: " + ", ".join(missing))
    return [env[n] for n in names]


def sdk_missing(adapter: str, module: str) -> ConfigRefused:
    return ConfigRefused(f"the {adapter} adapter needs the optional package '{module}', which is not "
                         f"installed; run: {PIP_HINT}")


def check_bindings_tier(platform: str, bindings: Mapping[str, Any]) -> None:
    """Alpha caps every SaaS chat adapter at T1 (spec §11.1; T2-on-SaaS deferred to §14).
    A leftover `riskAcceptance` block is refused rather than silently ignored."""
    if isinstance(bindings, Mapping) and "riskAcceptance" in bindings:
        raise ConfigRefused(f"bindings.riskAcceptance is not supported: {platform} is capped at T1 in alpha "
                            "(T2 on SaaS chat is deferred, spec §14)")


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
    return bool(APPROVAL_ID_RE.fullmatch(approval_id) and NONCE_RE.fullmatch(nonce))


class SaasAdapterBase:
    """Queue-backed `events()` / outbound channel guard shared by slack and discord."""
    name = "?"
    hosting = "saas"
    max_tier = "T1"

    def __init__(self, bindings: Mapping[str, Any], transport: Any, *, env: Mapping[str, str] | None = None):
        env = os.environ if env is None else env
        check_bindings_tier(self.name, bindings or {})
        self.refs = bound_refs(bindings or {}, self.name)
        self._secrets = require_env(env, *self.SECRET_VARS)  # type: ignore[attr-defined]
        self._transport = transport if transport is not None else self._real_transport()
        self._secrets = ()                          # EXT-15: only the transport keeps the tokens
        self._inbox: queue.Queue = queue.Queue()
        self._bot_id: str | None = None
        self._overflow, self._overflow_lock = 0, threading.Lock()

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

    def _sink(self, raw: Any) -> None:
        """Called from the SDK thread. None (disconnect) always gets through; anything else is
        dropped and counted while INBOX_MAX events are already waiting."""
        if raw is not None and self._inbox.qsize() >= INBOX_MAX:
            with self._overflow_lock:
                self._overflow += 1
            return
        self._inbox.put(raw)

    def take_overflow(self) -> int:
        """Events dropped since the last call (the gateway audits them as `overflow`)."""
        with self._overflow_lock:
            count, self._overflow = self._overflow, 0
        return count

    def events(self) -> Iterator[Event]:
        self._transport.listen(self._sink)
        while True:
            raw = self._inbox.get()
            if raw is None:
                return
            try:
                ev = self.to_event(raw)
            except Exception as exc:  # noqa: BLE001 - EXT-12: one odd event must not end the stream
                print(f"{self.name}: dropped malformed platform event ({type(exc).__name__})", file=sys.stderr)
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

