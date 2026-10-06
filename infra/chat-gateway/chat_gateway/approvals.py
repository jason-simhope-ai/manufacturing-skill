"""Approval objects (§6, Q6): bound to an args hash, 30-min TTL, single use.

Alpha has no executable actions, so the gateway wires `NoopExecutor`; the
mechanism is still complete and tested:

* id `apv-<8hex>`, nonce 128-bit hex; the book stores only HMAC(key, id|nonce|args_hash).
* Decisions come only from structured `ApprovalClick` events, never chat text.
* A click counts only in the channel the card was posted to (`click.channel_ref`, EXT-03).
* One approver decides; at T2+ the approver must differ from the requester.
* Any later click on a decided / expired approval → "replay"; on a card voided by a freeze → "void".
* `resolve(..., may_execute=)` is asked just before the executor runs; False → "frozen" (P-03).
* Dual-approval configurations are refused at load (see core.validate_roster).
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal, Protocol

from . import tier_rank
from .adapters.base import ApprovalCard, ApprovalClick

Resolution = Literal["granted", "denied", "expired", "mismatch", "forbidden", "replay", "void", "frozen"]
TTL_S = 1800


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def args_hash(args: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(args).encode("utf-8")).hexdigest()


class Executor(Protocol):
    def execute(self, action: dict) -> object: ...


@dataclass
class NoopExecutor:
    """Alpha executor: records what *would* have run, does nothing."""
    calls: list[dict] = field(default_factory=list)

    def execute(self, action: dict) -> None:
        self.calls.append(action)


@dataclass
class _Pending:
    action: dict
    args_hash: str
    mac: str
    requester: str
    approvers: frozenset[str]
    tier: str
    twin_id: str
    channel_ref: str
    thread_ref: str | None
    expires_at: float
    canonical: str = ""          # canonical JSON of the whole action, frozen at creation
    done: bool = False
    void: bool = False           # voided by a freeze (P-04)


class ApprovalBook:
    def __init__(self, hmac_key: bytes, ttl_s: int = TTL_S, clock: Callable[[], float] = time.time,
                 token_hex: Callable[[int], str] = secrets.token_hex):
        self._key = hmac_key
        self.ttl_s = ttl_s
        self._clock = clock
        self._hex = token_hex
        self._book: dict[str, _Pending] = {}

    def _mac(self, approval_id: str, nonce: str, ahash: str) -> str:
        msg = f"{approval_id}|{nonce}|{ahash}".encode("utf-8")
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()

    def create(self, action: dict, requester: str, channel: str, approvers: Iterable[str], *,
               tier: str = "T1", twin_id: str = "", thread_ref: str | None = None) -> ApprovalCard:
        """`action` = {"name": str, "args": {...}}; `requester` = platform user ref."""
        approval_id = "apv-" + self._hex(4)
        nonce = self._hex(16)
        frozen = copy.deepcopy(dict(action))
        frozen.setdefault("args", {})
        canonical = _canonical(frozen)                 # raises TypeError for non-JSON args
        ahash = args_hash(frozen["args"])
        expires = self._clock() + self.ttl_s
        self._book[approval_id] = _Pending(
            action=frozen, canonical=canonical, args_hash=ahash, mac=self._mac(approval_id, nonce, ahash),
            requester=requester, approvers=frozenset(approvers), tier=tier, twin_id=twin_id,
            channel_ref=channel, thread_ref=thread_ref, expires_at=expires)
        lines = (f"動作：{action.get('name', '?')}", f"參數雜湊：{ahash[:19]}…",
                 f"有效 {self.ttl_s // 60} 分鐘、一次性；只接受按鈕點擊")
        return ApprovalCard(approval_id, nonce, channel, thread_ref, lines, ahash, expires)

    def get(self, approval_id: str) -> _Pending | None:
        return self._book.get(approval_id)

    def pending(self) -> list[tuple[str, _Pending]]:
        """(id, record) of every card not yet decided, voided or expired."""
        now = self._clock()
        return [(aid, rec) for aid, rec in self._book.items() if not rec.done and now <= rec.expires_at]

    def void(self, approval_id: str) -> bool:
        """Void a pending card (freeze, P-04). A later click resolves "void"; nothing executes."""
        rec = self._book.get(approval_id)
        if rec is None or rec.done:
            return False
        rec.done = rec.void = True
        return True

    def resolve(self, click: ApprovalClick, executor: Executor, *, roles: Iterable[str] = (),
                action: dict | None = None, may_execute: Callable[[], bool] | None = None) -> Resolution:
        """Decide a click. `roles` = positions of the clicking user; `action`, if given,
        is what the caller is about to execute and must hash to the bound args. `may_execute`, if
        given, is asked right before an approved action runs; False voids the card ("frozen")."""
        rec = self._book.get(click.approval_id)
        if rec is None:
            return "mismatch"
        if rec.void and hmac.compare_digest(rec.mac, self._mac(click.approval_id, click.nonce, rec.args_hash)):
            return "void"
        if rec.done:
            return "replay"
        if not hmac.compare_digest(rec.mac, self._mac(click.approval_id, click.nonce, rec.args_hash)):
            return "mismatch"
        if click.channel_ref != rec.channel_ref:        # a copy of the card clicked elsewhere; not consumed
            return "mismatch"
        if self._clock() > rec.expires_at:
            rec.done = True
            return "expired"
        principals = {click.user_ref, *roles}
        if not rec.approvers & principals:
            return "forbidden"
        if tier_rank(rec.tier) >= tier_rank("T2") and click.user_ref == rec.requester:
            return "forbidden"
        if action is not None and args_hash(action.get("args", {})) != rec.args_hash:
            return "mismatch"
        try:   # the executed action must be byte-identical to what was hashed at creation
            now_canonical = _canonical(rec.action)
        except (TypeError, ValueError):
            now_canonical = None
        to_run = json.loads(rec.canonical)
        if now_canonical != rec.canonical or args_hash(to_run.get("args", {})) != rec.args_hash:
            rec.done = True
            return "mismatch"
        if click.decision != "approve":
            rec.done = True
            return "denied"
        if may_execute is not None and not may_execute():
            rec.done = rec.void = True
            return "frozen"
        rec.done = True
        executor.execute(to_run)
        return "granted"
