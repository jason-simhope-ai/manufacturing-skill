"""Gateway core (§3.3, §6, §9): roster loading, routing, policy, invocation, audit.

Data flow per inbound message:

    dedupe → bot/DM/external/unbound/no-@/unknown-identity filters → rate limit
    → @-route → asker check → DLP → taint (envelopes + tripwire + window)
    → effective autonomy → driver.run → result validation → formatter
    → output filter → audit msg_out → Reply

`Gateway.handle(event)` is pure with respect to the adapter: it returns what to
post; `Gateway.run()` does the posting.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import secrets
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from . import (ALPHA_MAX_AUTONOMY, AUTONOMY, EXIT_T3, READ_ONLY_TOOLS, TIERS, ConfigRefused,
               autonomy_rank, min_autonomy, tier_rank)
from . import sanitize
from .adapters.base import (ApprovalCard, ApprovalClick, ChatAdapter, Event, InboundMessage,
                            Reply, ScheduledPost)
from .approvals import ApprovalBook, Executor, NoopExecutor, args_hash
from .audit import AuditLog
from .drivers.base import DriverError, HarnessDriver, TwinInvocation, TwinResult
from .formatter import format_reply, notice
from .patterns import find_secrets
from .prompt import PROMPT_BUDGET_BYTES

__all__ = [
    "ApprovalCard", "ApprovalClick", "ConfigRefused", "Event", "Gateway", "InboundMessage",
    "Reply", "ScheduledPost", "TwinInvocation", "TwinResult", "effective_autonomy",
    "load_roster", "validate_roster", "RateLimiter", "synthetic_mock_identities",
]

MAX_CONFIG_BYTES = 1_000_000
TIER_CAP = {"T0": "act", "T1": "act", "T2": "act-with-approval", "T3": "draft"}
LOCAL_DRIVERS = frozenset({"mock"})
ALPHA_MAX_OFFPREM_TIER = "T1"     # SaaS chat platforms and cloud models: T1 at most in alpha
T3_DOC = "docs/superpowers/specs/2026-10-05-digital-twin-team-design.md §11.2"
T3_REPLY = "此內容可能屬 T3，不在本系統處理範圍，請依貴公司 T3 程序處理"
_TEXT_APPROVAL = re.compile(r"^\s*(?:核准|批准|同意|approved?|lgtm)\s*[。.!！]?\s*$", re.IGNORECASE)


# ── roster loading ───────────────────────────────────────────────────
def _read_json(path: Path, what: str) -> dict:
    if not path.is_file():
        raise ConfigRefused(f"{what} not found: {path}")
    if path.stat().st_size > MAX_CONFIG_BYTES:
        raise ConfigRefused(f"{what} larger than {MAX_CONFIG_BYTES} B: {path}")
    raw = path.read_text(encoding="utf-8")
    found = find_secrets(raw)
    if found:
        raise ConfigRefused(f"{what} contains a suspected token ({', '.join(found)}); refusing to start")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigRefused(f"{what} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigRefused(f"{what} must be a JSON object")
    return data


def load_roster(path: str | Path) -> dict:
    """Load `team/.build/roster.json` (+ sibling identities.json / bindings.json).

    Raises ConfigRefused(exit=3) for any T3 channel/twin, exit=78 for every other
    refusal (bad schema, act*, dual approval, prompt hash/budget, suspected token).
    """
    p = Path(path).expanduser().resolve()
    roster = validate_roster(_read_json(p, "roster"), p.parent)
    for name in ("identities", "bindings"):
        side = p.parent / f"{name}.json"
        roster[f"_{name}"] = _read_json(side, name) if side.is_file() else {}
    return roster


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ConfigRefused(msg)


def validate_roster(roster: dict, base_dir: Path) -> dict:
    """Validate a parsed roster.json; returns a copy with `_prompts` = {twin_id: abs path}."""
    _need(isinstance(roster, dict), "roster must be an object")
    channels, twins = roster.get("channels") or [], roster.get("twins") or []
    _need(isinstance(channels, list) and isinstance(twins, list), "channels/twins must be lists")
    t3 = [f"channel {c.get('id')}" for c in channels if isinstance(c, dict) and c.get("tier") == "T3"]
    t3 += [f"twin {t.get('id')}" for t in twins if isinstance(t, dict) and t.get("tierCeiling") == "T3"]
    if t3:
        raise ConfigRefused(f"T3 is refused in alpha ({', '.join(t3)}); see {T3_DOC}", exit=EXIT_T3)
    _need(roster.get("schema") == 1, "roster schema must be 1")
    policy = roster.get("policy")
    _need(isinstance(policy, dict), "roster.policy missing")
    for key in ("saasTierCeiling", "cloudTierCeiling"):
        _need(policy.get(key) in TIERS, f"policy.{key} must be a tier")
        # Alpha hard cap (§11.1): SaaS chat and cloud models never see T2+ (lint E047 too).
        _need(tier_rank(policy[key]) <= tier_rank(ALPHA_MAX_OFFPREM_TIER),
              f"policy.{key} {policy[key]} is above {ALPHA_MAX_OFFPREM_TIER}; refused in alpha")
    window = policy.get("channelWindow", 10)
    _need(isinstance(window, int) and 1 <= window <= 20, "policy.channelWindow must be 1–20")

    def autonomy_ok(value: object, where: str) -> None:
        _need(value in AUTONOMY, f"{where}: unknown autonomy {value!r}")
        _need(autonomy_rank(value) <= autonomy_rank(ALPHA_MAX_AUTONOMY),
              f"{where}: {value} is defined but refused in alpha (max {ALPHA_MAX_AUTONOMY})")

    autonomy_ok(policy.get("autonomyCeiling"), "policy.autonomyCeiling")
    for holder in [policy, *channels]:
        _need(not holder.get("dualApproval") and int(holder.get("approvalsRequired", 1)) <= 1,
              "dual-approval configurations are refused in alpha")
    prompts: dict[str, str] = {}
    base = base_dir.resolve()
    for t in twins:
        tid = t.get("id")
        _need(isinstance(tid, str) and bool(tid), "twin without id")
        _need(t.get("tierCeiling") in TIERS, f"twin {tid}: bad tierCeiling")
        _need(isinstance(t.get("title"), str), f"twin {tid}: title missing")
        autonomy_ok(t.get("effectiveCeiling"), f"twin {tid}.effectiveCeiling")
        caps = t.get("capabilities") or []
        _need(isinstance(caps, list) and caps, f"twin {tid}: no capabilities")
        for c in caps:
            autonomy_ok(c.get("autonomy"), f"twin {tid}.{c.get('id')}")
        _need(int((t.get("outsource") or {}).get("enabled", 0)) <= 1, f"twin {tid}: >1 enabled outsource (E034)")
        rel = t.get("prompt", "")
        _need(isinstance(rel, str) and rel and not rel.startswith(("/", "\\")) and ".." not in Path(rel).parts,
              f"twin {tid}: prompt path must be relative inside the roster dir")
        ppath = (base / rel).resolve()
        _need(ppath.is_relative_to(base) and ppath.is_file(), f"twin {tid}: prompt file missing: {rel}")
        data = ppath.read_bytes()
        _need(len(data) <= PROMPT_BUDGET_BYTES, f"twin {tid}: prompt {len(data)} B > {PROMPT_BUDGET_BYTES} B")
        sha = "sha256:" + hashlib.sha256(data).hexdigest()
        _need(sha == t.get("promptSha"), f"twin {tid}: promptSha mismatch (rebuild with team/tools/build.py)")
        prompts[tid] = str(ppath)
    ids = set(prompts)
    for c in channels:
        cid = c.get("id")
        _need(c.get("tier") in TIERS, f"channel {cid}: bad tier")
        autonomy_ok(c.get("autonomyCeiling"), f"channel {cid}.autonomyCeiling")
        _need(set(c.get("twins") or []) <= ids and c.get("twins"), f"channel {cid}: unknown twins")
        _need(c.get("defaultTwin") in c["twins"], f"channel {cid}: defaultTwin not in twins")
        for tid in c["twins"]:
            twin_tier = next(t["tierCeiling"] for t in twins if t["id"] == tid)
            _need(tier_rank(c["tier"]) <= tier_rank(twin_tier), f"channel {cid}: tier > twin {tid} tierCeiling (E042)")
        askers = c.get("askers")
        _need(askers == "members" or isinstance(askers, list), f"channel {cid}: askers must be 'members' or a list")
    out = dict(roster)
    out["_prompts"] = prompts
    return out


def synthetic_mock_identities(roster: dict) -> dict:
    """Mock-only fallback when no identities.json was built (example roster): one
    synthetic user `mock-<position>` per position the roster's channels name."""
    positions: set[str] = set()
    for c in roster.get("channels") or []:
        for key in ("askers", "approvers", "requesters"):
            if isinstance(c.get(key), list):
                positions.update(str(x) for x in c[key])
    positions.update(str(t.get("id")) for t in roster.get("twins") or [] if t.get("id"))
    return {"synthetic": True, "users": [{"platform": "mock", "userId": f"mock-{p}", "positions": [p]}
                                         for p in sorted(positions)]}


# ── autonomy ─────────────────────────────────────────────────────────
def effective_autonomy(cap: dict, twin: dict, policy: dict, channel: dict, *, asker: bool = True,
                       tainted: bool = False, degraded: bool = False) -> str | None:
    """min(capability, twin ceiling (file ∧ position, folded by build), policy, channel,
    tierCap, requesterCap) with outsource ≤ draft, VACANT → observe, tainted ≤ suggest.
    Returns None when the requester is not an asker (refuse)."""
    if not asker:
        return None
    levels = [cap["autonomy"], twin.get("effectiveCeiling", ALPHA_MAX_AUTONOMY), policy["autonomyCeiling"],
              channel["autonomyCeiling"], TIER_CAP[channel["tier"]], "draft", ALPHA_MAX_AUTONOMY]
    if cap.get("category") == "outsource":
        levels.append("draft")
    if twin.get("vacant"):
        levels.append("observe")
    if tainted:
        levels.append("suggest")
    if degraded:
        levels.append("observe")
    return min_autonomy(*levels)


def tools_for(autonomy: str, tainted: bool) -> tuple[str, ...]:
    """Alpha: always read-only. A tainted turn can never gain anything beyond read-only."""
    return READ_ONLY_TOOLS


# ── rate limiting ────────────────────────────────────────────────────
class RateLimiter:
    """Sliding-window counter: at most `limit` hits per `window_s` seconds per key."""

    def __init__(self, limit: int, window_s: float):
        self.limit, self.window_s = limit, window_s
        self._hits: dict[str, deque] = {}

    def _q(self, key: str, now: float) -> deque:
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window_s:
            q.popleft()
        return q

    def check(self, key: str, now: float) -> bool:
        return len(self._q(key, now)) < self.limit

    def hit(self, key: str, now: float) -> None:
        self._q(key, now).append(now)

    def allow(self, key: str, now: float) -> bool:
        ok = self.check(key, now)
        if ok:
            self.hit(key, now)
        return ok

    def dump(self) -> dict:
        return {k: list(q) for k, q in self._hits.items() if q}

    def load(self, data: dict) -> None:
        self._hits = {str(k): deque(float(x) for x in v) for k, v in data.items()}


# ── gateway ──────────────────────────────────────────────────────────
@dataclass
class _Ctx:
    event_id: str | None = None
    platform: str | None = None
    channel_id: str | None = None
    channel_ref: str | None = None
    tier: str | None = None
    thread: str | None = None
    operator: str = "role:unknown"
    operator_ref: str | None = None
    user_ref: str = ""
    positions: list[str] = field(default_factory=list)


class Gateway:
    """`Gateway(roster, adapter, driver, audit, clock).handle(event) -> list[Reply | ApprovalCard]`.

    Raises ConfigRefused at construction when the adapter / driver cannot serve
    the roster's channels (tier vs adapter max_tier / SaaS / cloud ceilings, or a
    failing `driver.self_check()`).
    """

    USER_LIMIT = (6, 60.0)            # 6 messages / user / minute
    CHANNEL_LIMIT = (60, 3600.0)      # 60 messages / channel / hour
    POST_LIMIT = (3, 86400.0)         # 3 scheduled posts / channel / day
    DEDUPE = (600.0, 1000)            # event_id kept 10 min or 1,000 entries
    FAILURES_TO_DEGRADE = 3

    def __init__(self, roster: dict, adapter: ChatAdapter, driver: HarnessDriver, audit: AuditLog,
                 clock: Callable[[], float] = time.time, *, approvals: ApprovalBook | None = None,
                 executor: Executor | None = None, token_hex: Callable[[int], str] = secrets.token_hex,
                 read_roots: tuple[str, ...] = (), daily_budget_usd: float | None = None,
                 extra_dlp: Iterable[tuple[str, re.Pattern]] = (), max_budget_usd: float = 0.10,
                 timeout_s: int = 60):
        self.roster, self.adapter, self.driver, self.audit, self.clock = roster, adapter, driver, audit, clock
        self.policy = roster["policy"]
        self.twins = {t["id"]: t for t in roster["twins"]}
        self.prompts = roster.get("_prompts", {})
        self.aliases: dict[str, str] = {}
        for t in roster["twins"]:
            for name in [t["id"], t["title"], *t.get("aliases", [])]:
                self.aliases[sanitize.normalize_for_match(name)] = t["id"]
        self.channels = {c["id"]: c for c in roster["channels"] if c.get("adapter") == adapter.name}
        bindings = (roster.get("_bindings") or {}).get("channels", {})
        self._chan_by_ref = {(b["platform"], b["ref"]): cid for cid, b in bindings.items() if cid in self.channels}
        self._ref_by_chan = {cid: b["ref"] for cid, b in bindings.items() if cid in self.channels}
        self._users = {(u["platform"], u["userId"]): u for u in (roster.get("_identities") or {}).get("users", [])}
        self.approvals = approvals or ApprovalBook(secrets.token_bytes(32), clock=clock, token_hex=token_hex)
        self.executor = executor or NoopExecutor()
        self._hex, self.read_roots, self.extra_dlp = token_hex, tuple(read_roots), tuple(extra_dlp)
        self.daily_budget_usd, self.max_budget_usd, self.timeout_s = daily_budget_usd, max_budget_usd, timeout_s
        self._windows: dict[str, deque] = {}
        self._seen: OrderedDict[str, float] = OrderedDict()
        self.user_rl = RateLimiter(*self.USER_LIMIT)
        self.channel_rl = RateLimiter(*self.CHANNEL_LIMIT)
        self.post_rl = RateLimiter(*self.POST_LIMIT)
        self._rl_noticed: dict[str, float] = {}
        self._failures: dict[str, int] = {}
        self._spend: dict[tuple[str, str], float] = {}
        self.last_deny: tuple[str, str, int] | None = None
        self._startup_checks()

    # ── startup ──
    def _startup_checks(self) -> None:
        problems = []
        cloud = self.driver.name not in LOCAL_DRIVERS
        for cid, c in self.channels.items():
            if tier_rank(c["tier"]) > tier_rank(self.adapter.max_tier):
                problems.append(f"channel {cid} tier {c['tier']} > adapter {self.adapter.name} max {self.adapter.max_tier}")
            if self.adapter.hosting == "saas" and tier_rank(c["tier"]) > tier_rank(self.policy["saasTierCeiling"]):
                problems.append(f"channel {cid} tier {c['tier']} > saasTierCeiling")
            if cloud and tier_rank(c["tier"]) > tier_rank(self.policy["cloudTierCeiling"]):
                problems.append(f"channel {cid} tier {c['tier']} > cloudTierCeiling for driver {self.driver.name}")
        problems += [f"driver self_check: {p}" for p in self.driver.self_check()]
        if problems:
            self._audit("config_refused", None, decision="deny", deny_reason="; ".join(problems)[:500])
            raise ConfigRefused("; ".join(problems))
        self._audit("config_loaded", None, decision="allow")

    # ── helpers ──
    def _audit(self, action: str, ctx: _Ctx | None, **kw) -> int:
        rec: dict = {"action": action, "ts": round(self.clock(), 3), "driver": self.driver.name}
        if ctx:
            rec.update(event_id=ctx.event_id, platform=ctx.platform, channel=ctx.channel_id,
                       channel_tier=ctx.tier, thread=ctx.thread, operator=ctx.operator,
                       operator_ref=ctx.operator_ref)
        rec.update(kw)
        return self.audit.append(**rec)

    def _say(self, ctx: _Ctx, twin_id: str, text_for_seq: Callable[[int], str], **kw) -> Reply:
        seq = self.audit.next_seq
        text = text_for_seq(seq)
        tier = ctx.tier or "sys"
        got = self._audit("msg_out", ctx, twin=twin_id or None, decision=kw.pop("decision", "allow"),
                          content_sha256=self.audit.content_tag(text),
                          content_len=None if tier in ("T2", "T3") else len(text), **kw)
        if got != seq:
            raise RuntimeError("audit seq raced")
        return Reply(ctx.channel_ref or "", ctx.thread, text, twin_id, seq)

    def _notice(self, ctx: _Ctx, twin_id: str, text: str, **kw) -> Reply:
        title = self.twins[twin_id]["title"] if twin_id in self.twins else None
        return self._say(ctx, twin_id, lambda seq: notice(title, text, seq), **kw)

    def _deny(self, ctx: _Ctx, reason: str, action: str = "policy_denied", **kw) -> list:
        seq = self._audit(action, ctx, decision="deny", deny_reason=reason, **kw)
        self.last_deny = (action, reason, seq)
        return []

    def _is_replay(self, event_id: str, now: float) -> bool:
        ttl, cap = self.DEDUPE
        while self._seen and (len(self._seen) > cap or next(iter(self._seen.values())) < now - ttl):
            self._seen.popitem(last=False)
        if event_id in self._seen:
            return True
        self._seen[event_id] = now
        return False

    def _identify(self, ctx: _Ctx, platform: str, user_ref: str, now: float) -> bool:
        ctx.user_ref, ctx.operator_ref = user_ref, self.audit.operator_ref(platform, user_ref)
        user = self._users.get((platform, user_ref))
        if not user:
            return False
        today = _dt.datetime.fromtimestamp(now, _dt.timezone.utc).date().isoformat()
        ctx.positions = list(user.get("positions", [])) + [
            a["role"] for a in user.get("actingFor", []) if str(a.get("until", "")) >= today]
        ctx.operator = f"role:{ctx.positions[0]}" if ctx.positions else "role:unknown"
        return True

    def _channel_for(self, platform: str, channel_ref: str) -> str | None:
        cid = self._chan_by_ref.get((platform, channel_ref))
        if cid is None and platform == "mock" and channel_ref in self.channels:
            cid = channel_ref
        return cid

    def _window(self, cid: str) -> deque:
        return self._windows.setdefault(cid, deque(maxlen=self.policy.get("channelWindow", 10)))

    # ── dispatch ──
    def handle(self, event: Event) -> list[Reply | ApprovalCard]:
        if isinstance(event, InboundMessage):
            return self._message(event)
        if isinstance(event, ApprovalClick):
            return self._click(event)
        if isinstance(event, ScheduledPost):
            return self._scheduled(event)
        raise TypeError(f"unknown event type {type(event).__name__}")

    def run(self, pace: float = 0.0) -> int:
        """Drive the adapter until its event stream ends; returns number of events."""
        n = 0
        try:
            for ev in self.adapter.events():
                n += 1
                self.last_deny = None
                outs = self.handle(ev)
                for out in outs:
                    (self.adapter.post_approval if isinstance(out, ApprovalCard) else self.adapter.post)(out)
                dropped = getattr(self.adapter, "notice_dropped", None)   # mock REPL only: never silent
                if not outs and self.last_deny and callable(dropped):
                    dropped(*self.last_deny)
                if pace:
                    time.sleep(pace)
        finally:
            self.adapter.close()
        return n

    # ── inbound message ──
    def _message(self, ev: InboundMessage) -> list[Reply | ApprovalCard]:
        now = self.clock()
        ctx = _Ctx(event_id=ev.event_id, platform=ev.platform, thread=ev.thread_ref or ev.event_id)
        if self._is_replay(ev.event_id, now):
            return self._deny(ctx, "duplicate_event", action="replay_rejected")
        for flag, reason in ((ev.author_is_bot, "bot_author"), (ev.is_dm, "dm"),
                             (ev.external_shared, "external_shared")):
            if flag:
                return self._deny(ctx, reason)
        cid = self._channel_for(ev.platform, ev.channel_ref)
        if cid is None:
            return self._deny(ctx, "unbound_channel")
        channel = self.channels[cid]
        ctx.channel_id, ctx.channel_ref, ctx.tier = cid, ev.channel_ref, channel["tier"]
        if not ev.mentions_bot:
            return self._deny(ctx, "no_mention")
        if not self._identify(ctx, ev.platform, ev.user_ref, now):
            return self._deny(ctx, "unknown_identity")
        text = sanitize.sanitize_for_model(ev.text)      # no NFKC: full-width punctuation kept
        self._audit("msg_in", ctx, content_sha256=self.audit.content_tag(text),
                    content_len=None if tier_rank(ctx.tier) >= 2 else len(text))
        ukey = f"{ev.platform}:{ev.user_ref}"
        ok_u, ok_c = self.user_rl.check(ukey, now), self.channel_rl.check(cid, now)
        if not (ok_u and ok_c):
            self._deny(ctx, "user_6_per_min" if not ok_u else "channel_60_per_hour", action="rate_limited")
            if now - self._rl_noticed.get(ukey, -1e18) >= 60:
                self._rl_noticed[ukey] = now
                return [self._notice(ctx, "", "訊息太頻繁，請稍候再 @（每人每分鐘 6 則、每頻道每小時 60 則）",
                                     decision="deny")]
            return []
        self.user_rl.hit(ukey, now)
        self.channel_rl.hit(cid, now)

        head, rest = (text.strip().split(None, 1) + [""])[:2] if text.strip() else ("", "")
        twin_id = self.aliases.get(sanitize.normalize_for_match(head).lstrip("@"))
        if twin_id is None:
            twin_id, rest = channel["defaultTwin"], text.strip()
        rest = rest.strip()
        if twin_id not in channel["twins"]:
            self._audit("route_decision", ctx, twin=twin_id, decision="deny", deny_reason="twin_not_in_channel")
            names = "、".join(f"【{self.twins[t]['title']}】" for t in channel["twins"])
            return [self._notice(ctx, "", f"這個分身不在本頻道。本頻道可用：{names}", decision="deny")]
        self._audit("route_decision", ctx, twin=twin_id, decision="allow")
        askers = channel["askers"]
        if askers != "members" and not set(ctx.positions) & set(askers):
            self._deny(ctx, "not_asker", twin=twin_id)
            return [self._notice(ctx, twin_id, "你的職位不在本頻道的提問名單，分身不回答", decision="deny")]
        if _TEXT_APPROVAL.match(sanitize.normalize_for_match(rest)):
            self._deny(ctx, "text_approval", twin=twin_id)
            return [self._notice(ctx, twin_id, "聊天文字不能核准任何事；核准只接受核准卡上的按鈕點擊",
                                 decision="deny")]
        hit_tier = sanitize.dlp_tier(rest, self.extra_dlp)
        if hit_tier and tier_rank(hit_tier) > tier_rank(ctx.tier):
            self._deny(ctx, f"dlp:{hit_tier}", action="dlp_blocked", twin=twin_id)
            msg = T3_REPLY if hit_tier == "T3" else (
                f"內容含 {hit_tier} 標記，不能在 {ctx.tier} 頻道處理；請改到正確分級的頻道（內容未送進模型）")
            return [self._notice(ctx, twin_id, msg, decision="deny")]

        rest, forged = sanitize.strip_envelopes(rest)
        hits = sanitize.tripwire_hits(rest) + (["envelope_forgery"] if forged else [])
        user_text, n_untrusted = sanitize.build_user_text(rest, lambda: self._hex(16))
        own_taint = bool(hits or n_untrusted)
        if hits:
            self._audit("injection_flag", ctx, twin=twin_id, decision="deny",
                        deny_reason=",".join(hits), tainted=True)
        return self._invoke(ctx, self.twins[twin_id], channel, user_text, own_taint, rest)

    # ── scheduled post ──
    def _scheduled(self, ev: ScheduledPost) -> list[Reply | ApprovalCard]:
        ctx = _Ctx(event_id=f"post:{ev.twin_id}:{ev.capability_id}", platform=self.adapter.name,
                   operator="role:scheduler")
        channel, twin = self.channels.get(ev.channel_id), self.twins.get(ev.twin_id)
        if not channel or not twin or ev.twin_id not in channel["twins"]:
            return self._deny(ctx, "scheduled_post_unbound")
        ctx.channel_id, ctx.tier = ev.channel_id, channel["tier"]
        ctx.channel_ref = self._ref_by_chan.get(ev.channel_id, ev.channel_id)
        cap = next((c for c in twin["capabilities"] if c["id"] == ev.capability_id and not c.get("dormant")), None)
        if cap is None:
            return self._deny(ctx, "unknown_capability", twin=twin["id"])
        if not self.post_rl.allow(ev.channel_id, self.clock()):
            return self._deny(ctx, "posts_3_per_day", action="rate_limited", twin=twin["id"])
        text = f"[排程] {cap['id']}"
        return self._invoke(ctx, twin, channel, text, False, text, cap=cap)

    # ── driver invocation (shared) ──
    def _invoke(self, ctx: _Ctx, twin: dict, channel: dict, user_text: str, own_taint: bool,
                plain: str, cap: dict | None = None) -> list[Reply | ApprovalCard]:
        tid = twin["id"]
        window = self._window(ctx.channel_id)
        tainted = own_taint or any(e.get("tainted") for e in window)
        caps = [c for c in twin["capabilities"] if not c.get("dormant")]
        cap = cap or next((c for c in caps if c["id"] in plain), caps[0])
        predict_first = "我先說" in plain and bool(cap.get("predictFirstEligible"))
        degraded = self._failures.get(tid, 0) >= self.FAILURES_TO_DEGRADE
        level = effective_autonomy(cap, twin, self.policy, channel, tainted=tainted, degraded=degraded)
        day = _dt.datetime.fromtimestamp(self.clock(), _dt.timezone.utc).date().isoformat()
        if self.daily_budget_usd is not None and self._spend.get((tid, day), 0.0) >= self.daily_budget_usd:
            self._deny(ctx, "daily_budget", twin=tid)
            return [self._notice(ctx, tid, "今日預算已用完，明天再問", decision="deny")]
        common = dict(twin=tid, twin_prompt_sha=twin.get("promptSha"), capability=cap["id"],
                      category=cap.get("category"), effective_autonomy=level, tainted=tainted)
        if not self._prompt_intact(tid, twin.get("promptSha")):
            self._audit("driver_error", ctx, decision="deny", deny_reason="prompt_sha_mismatch", **common)
            return [self._notice(ctx, tid, "暫時無法回應", decision="deny")]
        inv = TwinInvocation(
            twin_id=tid, prompt_path=self.prompts.get(tid, ""), user_text=user_text, prompt_sha=twin.get("promptSha"),
            channel_window=tuple(dict(e) for e in window), tier=channel["tier"], effective_autonomy=level,
            tools=tools_for(level, tainted), read_roots=self.read_roots, tainted=tainted,
            predict_first=predict_first, timeout_s=self.timeout_s, max_budget_usd=self.max_budget_usd)
        started = time.perf_counter()
        try:
            result = self.driver.run(inv)
            if not isinstance(result, TwinResult):
                raise DriverError("driver returned a non-TwinResult")
        except Exception as exc:  # noqa: BLE001 - any driver failure is reported, never guessed
            self._failures[tid] = self._failures.get(tid, 0) + 1
            self._audit("driver_error", ctx, decision="deny", deny_reason=type(exc).__name__, **common)
            return [self._notice(ctx, tid, "暫時無法回應", decision="deny")]
        latency = int((time.perf_counter() - started) * 1000)
        self._failures[tid] = 0
        result, fixes = self._validate(ctx, result, common)
        add_generic = autonomy_rank(level) >= autonomy_rank("suggest") and not result.decision_points
        if add_generic:
            fixes.append("decision_points")
        if fixes:
            self._audit("format_fixed", ctx, deny_reason=",".join(fixes), **common)
        sugg = result.suggest_twin if result.suggest_twin in self.twins and result.suggest_twin != tid else None
        seq = self.audit.next_seq
        text, stats = sanitize.filter_output(format_reply(
            twin["title"], level, result, category=cap.get("category"), seq=seq, tainted=tainted,
            add_generic_decision=add_generic, suggest_title=self.twins[sugg]["title"] if sugg else None), ctx.tier,
            self.extra_dlp)
        if stats["blocked"]:
            self._audit("dlp_blocked", ctx, decision="deny", deny_reason=f"output:{stats['blocked']}", **common)
            text = None
        usage = dict(result.usage) if isinstance(result.usage, dict) else {}
        cost = float(usage.get("cost_usd", 0.0) or 0.0)
        self._spend[(tid, day)] = self._spend.get((tid, day), 0.0) + cost
        redactions = {"secret": stats["secret"], "pii": 0, "amount": 0}
        if text is None:
            reply = self._say(ctx, tid, lambda s: notice(twin["title"], "回覆含高於本頻道分級的標記，已整則攔截", s),
                              decision="deny", usage=usage, latency_ms=latency, redactions=redactions,
                              **{k: v for k, v in common.items() if k != "twin"})
        else:
            reply = self._say(ctx, tid, lambda s: text, usage=usage, latency_ms=latency, redactions=redactions,
                              **{k: v for k, v in common.items() if k != "twin"})
        window.append({"role": "user", "text": user_text, "tainted": own_taint})
        # The reply carries only this turn's own taint, so a taint leaves the channel once the
        # offending message rolls out of the window (it does not re-infect every later reply).
        window.append({"role": "twin", "twin": tid, "text": reply.text, "tainted": own_taint})
        return [reply]

    def _prompt_intact(self, tid: str, want: str | None) -> bool:
        """Re-hash the compiled prompt on every invocation (it was pinned at load)."""
        path = self.prompts.get(tid)
        if not path or not want:
            return False
        try:
            data = Path(path).read_bytes()
        except OSError:
            return False
        return "sha256:" + hashlib.sha256(data).hexdigest() == want

    def _validate(self, ctx: _Ctx, r: TwinResult, common: dict) -> tuple[TwinResult, list[str]]:
        fixes: list[str] = []
        conf = r.confidence
        if conf not in ("中", "低"):
            conf, fixes = "低", fixes + ["confidence"]
        if r.proposed_actions:
            ah = args_hash(list(r.proposed_actions))
            self._audit("tool_proposed", ctx, args_hash=ah, **common)
            self._audit("tool_denied", ctx, args_hash=ah, decision="deny",
                        deny_reason="tainted_turn" if common["tainted"] else "alpha_no_actions", **common)
        clean = TwinResult(reply=str(r.reply), citations=tuple(map(str, r.citations)),
                           assumed=tuple(map(str, r.assumed)), unverified=tuple(map(str, r.unverified)),
                           confidence=conf, decision_points=tuple(map(str, r.decision_points)),
                           proposed_actions=(), suggest_twin=r.suggest_twin, usage=r.usage)
        return clean, fixes

    # ── approvals ──
    def request_approval(self, channel_id: str, requester_ref: str, action: dict, *, twin_id: str = "",
                         thread_ref: str | None = None, tainted: bool = False) -> ApprovalCard | None:
        """Issue an approval card (unused by the alpha chat flow; executor is Noop).
        Tainted turns never get a card."""
        channel = self.channels[channel_id]
        ctx = _Ctx(channel_id=channel_id, channel_ref=self._ref_by_chan.get(channel_id, channel_id),
                   tier=channel["tier"], thread=thread_ref, operator_ref=self.audit.operator_ref(
                       self.adapter.name, requester_ref))
        if tainted:
            self._deny(ctx, "tainted_turn", action="tool_denied", twin=twin_id or None,
                       args_hash=args_hash(action.get("args", {})))
            return None
        card = self.approvals.create(action, requester_ref, ctx.channel_ref, channel.get("approvers", []),
                                     tier=channel["tier"], twin_id=twin_id, thread_ref=thread_ref)
        self._audit("approval_requested", ctx, twin=twin_id or None, args_hash=card.args_hash,
                    approval_id=card.approval_id)
        return card

    def _click(self, ev: ApprovalClick) -> list[Reply | ApprovalCard]:
        now = self.clock()
        rec = self.approvals.get(ev.approval_id)
        ctx = _Ctx(event_id=ev.event_id, platform=ev.platform, tier=rec.tier if rec else None,
                   channel_ref=rec.channel_ref if rec else None, thread=rec.thread_ref if rec else None)
        if self._is_replay(ev.event_id, now):
            return self._deny(ctx, "duplicate_event", action="replay_rejected", approval_id=ev.approval_id)
        self._identify(ctx, ev.platform, ev.user_ref, now)
        status = self.approvals.resolve(ev, self.executor, roles=ctx.positions)
        action, decision, reason = {
            "granted": ("approval_granted", "allow", None), "denied": ("approval_denied", "deny", "approver_denied"),
            "expired": ("approval_expired", "deny", "ttl"), "replay": ("replay_rejected", "deny", "single_use"),
            "mismatch": ("policy_denied", "deny", "approval_mismatch"),
            "forbidden": ("policy_denied", "deny", "approval_forbidden"),
        }[status]
        self._audit(action, ctx, approval_id=ev.approval_id, decision=decision, deny_reason=reason,
                    args_hash=rec.args_hash if rec else None)
        if rec is None:
            return []
        return [self._notice(ctx, rec.twin_id if rec.twin_id in self.twins else "", f"核准結果：{status}",
                             decision=decision)]
