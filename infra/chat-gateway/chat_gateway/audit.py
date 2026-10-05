"""Append-only, keyed (HMAC) hash-chained audit log (§9.6, §11.6).

Layout under the audit root:

    <tier>/audit.jsonl     one chain per tier (T0..T3, or `sys` for gateway-level events)
    checkpoint.json        signed per-tier heads: {tier: {count, seq, head}} + global seq

* `hash = "hmac-sha256:" + HMAC(chain_key(tier), prev_hash + "\\n" + canonical(record - hash))`.
  The chain key is derived from `MFG_TEAM_AUDIT_HMAC_KEY`, so nobody without the key can
  edit, delete, reorder or truncate records and recompute a chain that still verifies.
* `checkpoint.json` is rewritten (atomically) after every append and signed with a
  derived key. `verify` checks every tier file against it, so tail truncation, a deleted
  tier file and gaps in the global `seq` are detected. A checkpoint alone cannot stop a
  rollback of *both* the log and the checkpoint to an older state: copying the checkpoint
  off-host (or to write-once storage) on a schedule is the operator's job.
* `content_sha256` holds an HMAC content tag (`hmac-sha256:…`, derived key), not a plain
  hash, so short or templated messages cannot be recovered by dictionary from the log.
* No message text is ever stored: the field set is a fixed whitelist, and at T2+
  even `content_len` is dropped.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Callable

from . import ConfigRefused

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
VERSION = 2
PREFIX = "hmac-sha256:"
CHECKPOINT = "checkpoint.json"


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _subkey(key: bytes, label: str) -> bytes:
    return hmac.new(key, f"mfg-team-audit/{label}".encode("utf-8"), hashlib.sha256).digest()


def _mac(key: bytes, msg: str) -> str:
    return PREFIX + hmac.new(key, msg.encode("utf-8"), hashlib.sha256).hexdigest()


def record_mac(key: bytes, tier: str, record: dict) -> str:
    """Keyed chain value of `record` (its `hash` field excluded)."""
    body = {k: v for k, v in record.items() if k != "hash"}
    return _mac(_subkey(key, f"chain/{tier}"), str(record.get("prev_hash")) + "\n" + canonical_json(body))


def content_tag(key: bytes, text: str) -> str:
    """HMAC content tag stored in the `content_sha256` field (never a plain hash)."""
    return _mac(_subkey(key, "content"), text)


def _checkpoint_mac(key: bytes, body: dict) -> str:
    return _mac(_subkey(key, "checkpoint"), canonical_json(body))


def _read_records(path: Path) -> tuple[list[dict], str | None]:
    """All records of one tier file, or (records so far, problem)."""
    recs: list[dict] = []
    try:
        fh = path.open(encoding="utf-8")
    except OSError as exc:
        return recs, f"{path.name}: unreadable ({type(exc).__name__})"
    with fh:
        for n, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return recs, f"line {n}: not JSON"
            if not isinstance(rec, dict):
                return recs, f"line {n}: not a JSON object"
            recs.append(rec)
    return recs, None


def _load_checkpoint(root: Path, key: bytes) -> tuple[dict | None, str | None]:
    p = root / CHECKPOINT
    if not p.is_file():
        return None, "checkpoint.json missing"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "checkpoint.json unreadable"
    if not isinstance(data, dict) or not isinstance(data.get("tiers"), dict):
        return None, "checkpoint.json malformed"
    body = {k: v for k, v in data.items() if k != "mac"}
    if not isinstance(data.get("mac"), str) or not hmac.compare_digest(data["mac"], _checkpoint_mac(key, body)):
        return None, "checkpoint.json signature invalid (wrong key or edited)"
    return data, None


class AuditLog:
    """`AuditLog(root_dir, hmac_key).append(**fields) -> seq`.

    Resuming an existing log requires its checkpoint to verify with the same key;
    otherwise the gateway refuses to start (it would otherwise re-sign a tampered log).
    """

    def __init__(self, path: str | os.PathLike, hmac_key: bytes, clock: Callable[[], float] = time.time,
                 on_append: Callable[[dict], None] | None = None):
        self.root = Path(path).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._key = hmac_key
        self._clock = clock
        self.on_append = on_append
        self._tiers: dict[str, dict] = {}
        self._seq = 0
        existing = [k for k in _FILE_KEYS if (self.root / k / "audit.jsonl").is_file()]
        if existing or (self.root / CHECKPOINT).exists():
            ok, _n, problems = verify_report(self.root, hmac_key)
            if not ok:
                raise ConfigRefused("audit log does not verify against its checkpoint ("
                                    + "; ".join(problems[:3]) + "); run audit-verify and investigate")
            ckpt, _ = _load_checkpoint(self.root, hmac_key)
            self._tiers = {t: dict(v) for t, v in ckpt["tiers"].items()}
            self._seq = int(ckpt.get("seq", 0))

    @property
    def next_seq(self) -> int:
        return self._seq + 1

    def operator_ref(self, platform: str, user_id: str) -> str:
        mac = hmac.new(self._key, f"{platform}:{user_id}".encode("utf-8"), hashlib.sha256)
        return mac.hexdigest()[:16]

    def content_tag(self, text: str) -> str:
        return content_tag(self._key, text)

    def _write_checkpoint(self) -> None:
        body = {"v": VERSION, "seq": self._seq, "tiers": self._tiers}
        data = dict(body, mac=_checkpoint_mac(self._key, body))
        tmp = self.root / (CHECKPOINT + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(canonical_json(data) + "\n")
        os.replace(tmp, self.root / CHECKPOINT)

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
            fields["content_len"] = None          # T2+: content tag only
        self._seq += 1
        head = self._tiers.get(tier, {})
        rec = {k: None for k in FIELDS}
        rec.update(fields)
        rec.update(v=VERSION, seq=self._seq, prev_hash=head.get("head", GENESIS))
        if rec["ts"] is None:
            rec["ts"] = round(self._clock(), 3)
        rec["hash"] = record_mac(self._key, tier, rec)
        path = self.root / tier / "audit.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(canonical_json(rec) + "\n")
        self._tiers[tier] = {"count": int(head.get("count", 0)) + 1, "seq": self._seq, "head": rec["hash"]}
        self._write_checkpoint()
        if self.on_append:
            self.on_append(rec)
        return self._seq


def _verify_chain(recs: list[dict], tier: str, key: bytes) -> tuple[int, list[int], str | None]:
    prev, seqs = GENESIS, []
    for i, rec in enumerate(recs, 1):
        if rec.get("prev_hash") != prev:
            return i - 1, seqs, f"{tier} record {i}: prev_hash breaks the chain"
        got = rec.get("hash")
        if not isinstance(got, str) or not hmac.compare_digest(got, record_mac(key, tier, rec)):
            return i - 1, seqs, f"{tier} record {i}: MAC mismatch (edited, or wrong key)"
        seq = rec.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or (seqs and seq <= seqs[-1]):
            return i - 1, seqs, f"{tier} record {i}: seq not increasing"
        prev = got
        seqs.append(seq)
    return len(recs), seqs, None


def verify_report(path: str | os.PathLike, key: bytes) -> tuple[bool, int, list[str]]:
    """Verify an audit root directory (all tiers + checkpoint) or one `<tier>/audit.jsonl`.

    Returns (ok, records_verified, problems). A directory additionally requires the
    global `seq` to be contiguous from 1 to the checkpoint's last seq.
    """
    p = Path(path)
    single = p.is_file()
    root = p.parent.parent if single else p
    problems: list[str] = []
    ckpt, why = _load_checkpoint(root, key)
    if why:
        problems.append(why)
    tiers = [p.parent.name] if single else [k for k in _FILE_KEYS if (root / k / "audit.jsonl").is_file()]
    if not single:
        stray = sorted(d.name for d in root.glob("*/audit.jsonl") if d.parent.name not in _FILE_KEYS)
        problems += [f"unexpected tier file {s}/audit.jsonl" for s in stray]
    total, seen = 0, []
    for tier in tiers:
        recs, bad = _read_records(root / tier / "audit.jsonl")
        n, seqs, broken = _verify_chain(recs, tier, key)
        total += n
        seen += seqs
        problems += [f"{tier} {bad}"] if bad else []
        problems += [broken] if broken else []
        if ckpt is not None and not bad and not broken:
            want = ckpt["tiers"].get(tier)
            have = {"count": len(recs), "seq": seqs[-1] if seqs else None,
                    "head": recs[-1]["hash"] if recs else None}
            if want != have:
                problems.append(f"{tier}: file does not match checkpoint (truncated, rolled back or appended)")
    if ckpt is not None:
        expected = [p.parent.name] if single else list(ckpt["tiers"])
        missing = [t for t in expected if not (root / t / "audit.jsonl").is_file()]
        problems += [f"{t}/audit.jsonl missing (listed in checkpoint)" for t in missing]
        if not single and not problems:
            last = int(ckpt.get("seq", 0))
            if sorted(seen) != list(range(1, last + 1)):
                problems.append(f"global seq not contiguous 1..{last}")
    return not problems, total, problems


def verify(path: str | os.PathLike, key: bytes) -> tuple[bool, int]:
    """(ok, number_of_records). See `verify_report` for the problem list."""
    ok, n, _ = verify_report(path, key)
    return ok, n


def heads(path: str | os.PathLike, key: bytes) -> dict | None:
    """Signed checkpoint content (per-tier count/seq/head), for weekly sign-off; None if invalid."""
    p = Path(path)
    ckpt, _ = _load_checkpoint(p.parent.parent if p.is_file() else p, key)
    return None if ckpt is None else {"seq": ckpt.get("seq"), "tiers": ckpt["tiers"]}
