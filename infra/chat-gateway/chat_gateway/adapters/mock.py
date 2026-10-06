"""Mock adapter: scripted JSONL events or a console REPL; local, max tier T2 (§9.2).

Script lines (one JSON object each; unknown keys ignored; full field table in
infra/chat-gateway/README.md "Write your own replay script"). The whole script is
validated before anything runs: a bad line raises ScriptError naming the line number.

    {"type":"message","id":"m1","channel":"qa-floor","user":"mock-qa-lead","text":"@品保 …",
     "mention":true,"bot":false,"dm":false,"external":false,"thread":null,"ts":1790000000}
    {"type":"approval_click","id":"c1","approval_id":"apv-…","nonce":"…","user":"…","decision":"approve",
     "channel":"qa-floor"}
    {"type":"scheduled","twin":"qa-manager","capability":"spc-watch","channel":"qa-floor"}
    {"type":"note", …}   # narration for demo.py; passed to `on_note`, not an Event

REPL (no script): `<channel> <user> <text>`; text starting with `@` counts as a mention.
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
import time
from pathlib import Path
from typing import Callable, Iterator, TextIO

from .base import ApprovalCard, ApprovalClick, Event, InboundMessage, Reply, ScheduledPost

MAX_SCRIPT_BYTES = 2_000_000
STEP_S = 10.0   # replay: an event without "ts" lands this many seconds after the previous one

_REQUIRED = {"message": ("id",), "approval_click": ("id",), "scheduled": ("twin", "capability", "channel"),
             "note": ()}


class ScriptError(ValueError):
    """A replay-script line is unusable. The message is one line and starts with the line number."""


def _check(n: int, obj) -> dict:
    if not isinstance(obj, dict):
        raise ScriptError(f"script line {n}: expected a JSON object")
    kind = obj.get("type")
    if kind not in _REQUIRED:
        raise ScriptError(f"script line {n}: unknown type {kind!r} (use {', '.join(_REQUIRED)})")
    for key in _REQUIRED[kind]:
        if obj.get(key) in (None, ""):
            raise ScriptError(f'script line {n}: type "{kind}" needs "{key}"')
    if "ts" in obj:
        try:
            float(obj["ts"])
        except (TypeError, ValueError):
            raise ScriptError(f'script line {n}: "ts" must be a number (epoch seconds)') from None
    return obj


def _hhmm(ts: float, offset_h: int) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone(_dt.timedelta(hours=offset_h))).strftime("%H:%M")


class MockAdapter:
    name = "mock"
    hosting = "local"
    max_tier = "T2"

    def __init__(self, script: str | Path | list[dict] | None = None, out: TextIO = sys.stdout,
                 inp: TextIO = sys.stdin, on_note: Callable[[dict], None] | None = None,
                 clock: Callable[[], float] = time.time, tz_offset_h: int = 8):
        self.script, self.out, self.inp, self.on_note = script, out, inp, on_note
        self.clock, self.tz = clock, tz_offset_h
        self.compact = False
        self.last_ts = 0.0
        self.posted: list[Reply | ApprovalCard] = []

    # ── inbound ──
    def _lines(self) -> list[dict]:
        if isinstance(self.script, list):
            return [_check(n, o) for n, o in enumerate(self.script, 1)]
        path = Path(self.script)
        if not path.is_file() or path.stat().st_size > MAX_SCRIPT_BYTES:
            raise ValueError(f"mock script missing or too large: {path}")
        out = []
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ScriptError(f"script line {n}: invalid JSON ({exc.msg}, column {exc.colno})") from None
            out.append(_check(n, obj))
        return out

    def replay_clock(self) -> float:
        """Script time: the `ts` of the event being handled (wall clock until the first event)."""
        return self.last_ts or self.clock()

    def to_event(self, obj: dict) -> Event | None:
        """Pure mapping of one script object to an Event (None for notes / unknown)."""
        kind, ts = obj.get("type"), float(obj.get("ts", self.last_ts or self.clock()))
        if kind == "message":
            return InboundMessage(
                event_id=str(obj["id"]), platform="mock", channel_ref=str(obj.get("channel", "")),
                thread_ref=obj.get("thread"), user_ref=str(obj.get("user", "")), text=str(obj.get("text", "")),
                mentions_bot=bool(obj.get("mention", True)), author_is_bot=bool(obj.get("bot", False)),
                is_dm=bool(obj.get("dm", False)), external_shared=bool(obj.get("external", False)), ts=ts)
        if kind == "approval_click":
            return ApprovalClick(event_id=str(obj["id"]), platform="mock", approval_id=str(obj.get("approval_id", "")),
                                 nonce=str(obj.get("nonce", "")), user_ref=str(obj.get("user", "")),
                                 decision="approve" if obj.get("decision") == "approve" else "deny", ts=ts,
                                 channel_ref=str(obj.get("channel", "")))
        if kind == "scheduled":
            return ScheduledPost(twin_id=str(obj["twin"]), capability_id=str(obj["capability"]),
                                 channel_id=str(obj["channel"]))
        return None

    def _echo(self, ev: Event) -> None:
        t = _hhmm(self.last_ts, self.tz)
        if isinstance(ev, InboundMessage):
            flags = [n for n, f in (("bot", ev.author_is_bot), ("DM", ev.is_dm), ("external", ev.external_shared),
                                    ("no-@", not ev.mentions_bot)) if f]
            tag = f" [{', '.join(flags)}]" if flags else ""
            self.out.write(f"[{t}] #{ev.channel_ref} {ev.user_ref}{tag}: {ev.text}\n")
        elif isinstance(ev, ApprovalClick):
            self.out.write(f"[{t}] (button) {ev.user_ref} clicks {ev.decision} on {ev.approval_id}\n")
        else:
            self.out.write(f"[{t}] (cron) post --twin {ev.twin_id} --capability {ev.capability_id} "
                           f"--channel {ev.channel_id}\n")

    def events(self) -> Iterator[Event]:
        if self.script is None:
            yield from self._repl()
            return
        for obj in self._lines():
            if obj.get("type") == "note":
                if self.on_note:
                    self.on_note(obj)
                continue
            self.last_ts = float(obj["ts"]) if "ts" in obj else (
                self.last_ts + STEP_S if self.last_ts else self.clock())
            ev = self.to_event(obj)
            if ev is not None:
                self._echo(ev)
                yield ev

    def _repl(self) -> Iterator[Event]:
        n = 0
        self.out.write("mock REPL — '<channel> <user> <text>', text starting with @ = mention; Ctrl-D to quit\n"
                       "replies are canned keyword matches from the mock driver, not model output\n")
        for line in self.inp:
            parts = line.strip().split(maxsplit=2)
            if len(parts) < 3:
                continue
            n += 1
            self.last_ts = self.clock()
            text = parts[2]
            yield InboundMessage(f"repl-{n}", "mock", parts[0], None, parts[1], text.lstrip("@"),
                                 text.startswith("@"), False, False, False, self.last_ts)

    # ── outbound ──
    def post(self, reply: Reply) -> str:
        self.posted.append(reply)
        lines = reply.text.splitlines() or [""]
        if self.compact and len(lines) > 2:
            lines = [lines[0], "…", lines[-1]]
        where = f"#{reply.channel_ref}" + (f" thread:{reply.thread_ref}" if reply.thread_ref else "")
        self.out.write(f"  → {where}\n" + "".join(f"    {l}\n" for l in lines))
        return f"mock-msg-{len(self.posted)}"

    def post_approval(self, card: ApprovalCard) -> str:
        self.posted.append(card)
        self.out.write(f"  → approval card {card.approval_id} (expires {_hhmm(card.expires_at, self.tz)})\n"
                       + "".join(f"    {l}\n" for l in card.lines))
        return f"mock-card-{len(self.posted)}"

    def notice_dropped(self, action: str, reason: str, seq: int) -> None:
        """Mock only: say why nothing was posted (real adapters stay silent on denials)."""
        self.out.write(f"  (no reply: {action} {reason} · audit #{seq})\n")

    def close(self) -> None:
        self.out.flush()
