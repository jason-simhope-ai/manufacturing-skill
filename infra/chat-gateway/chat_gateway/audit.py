"""Append-only, hash-chained audit log (§9.6).

Layout: `<root>/<tier>/audit.jsonl` (tier ∈ T0..T3, or `sys` for gateway-level
events). `seq` is global across files; each file is its own hash chain starting
at `prev_hash = "sha256:0"`. No message text is ever stored: the field set is a
fixed whitelist, and at T2+ even `content_len` is dropped (hash only).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Callable

FIELDS = (
    "v", "ts", "seq", "event_id", "platform", "channel", "channel_tier", "thread",
    "operator", "operator_ref", "twin", "twin_prompt_sha", "driver", "action",
    "capability", "category", "effective_autonomy", "args_hash", "approval_id",
    "decision", "deny_reason", "content_sha256", "content_len", "redactions",
    "tainted", "usage", "latency_ms", "prev_hash", "hash",
)
ACTIONS = frozenset(
    "msg_in msg_out route_decision tool_proposed tool_denied approval_requested "
    "approval_granted approval_denied approval_expired injection_flag policy_denied "
    "rate_limited replay_rejected dlp_blocked format_fixed driver_error config_loaded "
    "config_refused".split()
)
_FILE_KEYS = ("T0", "T1", "T2", "T3", "sys")
GENESIS = "sha256:0"


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def record_hash(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def content_sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditLog:
    """`AuditLog(root_dir, hmac_key).append(**fields) -> seq`."""

    def __init__(self, path: str | os.PathLike, hmac_key: bytes, clock: Callable[[], float] = time.time,
                 on_append: Callable[[dict], None] | None = None):
        self.root = Path(path).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._key = hmac_key
        self._clock = clock
        self.on_append = on_append
        self._prev: dict[str, str] = {}
        self._seq = 0
        for key in _FILE_KEYS:                       # resume an existing chain
            last = _last_record(self.root / key / "audit.jsonl")
            if last:
                self._prev[key] = last["hash"]
                self._seq = max(self._seq, int(last["seq"]))

    @property
    def next_seq(self) -> int:
        return self._seq + 1

    def operator_ref(self, platform: str, user_id: str) -> str:
        mac = hmac.new(self._key, f"{platform}:{user_id}".encode("utf-8"), hashlib.sha256)
        return mac.hexdigest()[:16]

    def append(self, **fields) -> int:
        unknown = set(fields) - set(FIELDS)
        if unknown:
            raise ValueError(f"unknown audit fields: {sorted(unknown)}")
        if fields.get("action") not in ACTIONS:
            raise ValueError(f"unknown audit action: {fields.get('action')!r}")
        tier = fields.get("channel_tier") or "sys"
        if tier not in _FILE_KEYS:
            raise ValueError(f"bad tier {tier!r}")
        if tier in ("T2", "T3"):
            fields["content_len"] = None          # T2+: content hash only
        self._seq += 1
        rec = {k: None for k in FIELDS}
        rec.update(fields)
        rec.update(v=1, seq=self._seq, prev_hash=self._prev.get(tier, GENESIS))
        if rec["ts"] is None:
            rec["ts"] = round(self._clock(), 3)
        rec["hash"] = record_hash(rec)
        path = self.root / tier / "audit.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(canonical_json(rec) + "\n")
        self._prev[tier] = rec["hash"]
        if self.on_append:
            self.on_append(rec)
        return self._seq


def _last_record(path: Path) -> dict | None:
    if not path.is_file():
        return None
    last = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    return json.loads(last) if last else None


def _verify_file(path: Path) -> tuple[bool, int, list[int]]:
    prev, n, seqs = GENESIS, 0, []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return False, n, seqs
            if rec.get("prev_hash") != prev or rec.get("hash") != record_hash(rec):
                return False, n, seqs
            if seqs and rec["seq"] <= seqs[-1]:
                return False, n, seqs
            prev = rec["hash"]
            seqs.append(rec["seq"])
            n += 1
    return True, n, seqs


def verify(path: str | os.PathLike) -> tuple[bool, int]:
    """Verify one audit.jsonl, or every `<tier>/audit.jsonl` under a directory.

    Returns (ok, number_of_records). Global seq must be unique across files.
    """
    p = Path(path)
    files = [p] if p.is_file() else sorted(p.glob("*/audit.jsonl"))
    total, seen = 0, set()
    for f in files:
        ok, n, seqs = _verify_file(f)
        total += n
        if not ok or seen.intersection(seqs):
            return False, total
        seen.update(seqs)
    return True, total
