#!/usr/bin/env python3
"""Offline 8-beat demo of the chat gateway (§17.4): mock adapter + mock driver,
real routing / classification / rate-limit / approval / audit / taint code.

    python3 infra/chat-gateway/demo.py                       # print transcript
    python3 infra/chat-gateway/demo.py --check GOLDEN.txt    # exit 1 on any diff
    python3 infra/chat-gateway/demo.py --roster team/.build/roster.json   # other roster (golden won't match)

Zero credentials, zero network, deterministic (fixed clock, fixed ids, public
DEMO KEYS). Audit records go to a temporary directory that is removed on exit.
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import io
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import TextIO

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from chat_gateway import ConfigRefused  # noqa: E402
from chat_gateway.adapters.mock import MockAdapter  # noqa: E402
from chat_gateway.approvals import ApprovalBook  # noqa: E402
from chat_gateway.audit import AuditLog, verify  # noqa: E402
from chat_gateway.config import DEMO_APPROVAL_KEY, DEMO_AUDIT_KEY, config_from_env  # noqa: E402
from chat_gateway.core import Gateway, load_roster, validate_roster  # noqa: E402
from chat_gateway.drivers.mock import ASSUMED_USD_PER_MTOK, MockDriver  # noqa: E402
from chat_gateway.prompt import PROMPT_BUDGET_BYTES, estimate_tokens  # noqa: E402

DEMO_ROSTER = HERE / "fixtures" / "roster" / "roster.json"
DEMO_SCRIPT = HERE / "fixtures" / "demo.jsonl"
DEMO_IDENTITIES = HERE / "fixtures" / "roster" / "identities.json"   # used when a roster ships none
REPO = HERE.parents[1]
START_TS = 1791157800.0          # 2026-10-05 07:50 +08:00
BEATS = 8


class FixedClock:
    def __init__(self, t: float):
        self.t = t

    def __call__(self) -> float:
        return self.t


class DetHex:
    """Deterministic stand-in for secrets.token_hex (demo only)."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self, nbytes: int) -> str:
        self.n += 1
        return hashlib.sha256(f"demo-{self.n}".encode()).hexdigest()[: nbytes * 2]


def refusal_checks(out: TextIO, roster_path: Path) -> None:
    raw = json.loads(roster_path.read_text(encoding="utf-8"))
    base = roster_path.parent

    def attempt(label: str, fn) -> None:
        try:
            fn()
            out.write(f"  {label} → started (UNEXPECTED)\n")
        except ConfigRefused as exc:
            out.write(f"  {label} → refused, exit {exc.exit}: {exc}\n")

    t3 = copy.deepcopy(raw)
    twin = t3["twins"][0]["id"]
    t3["channels"].append({**t3["channels"][0], "id": "special-project", "tier": "T3", "twins": [twin],
                           "defaultTwin": twin})
    attempt("T3 頻道 special-project", lambda: validate_roster(t3, base))
    act = copy.deepcopy(raw)
    act["twins"][0]["capabilities"][0]["autonomy"] = "act-with-approval"
    attempt("能力 autonomy=act-with-approval", lambda: validate_roster(act, base))
    tampered = copy.deepcopy(raw)
    tampered["twins"][0]["promptSha"] = "sha256:" + "0" * 64
    attempt("分身 prompt 雜湊不符", lambda: validate_roster(tampered, base))
    attempt("slack adapter 但未設 HMAC 金鑰", lambda: config_from_env({}, adapter="slack"))


def run_demo(out: TextIO, roster_path: Path, pace: float = 0.0) -> int:
    clock, hexgen = FixedClock(START_TS), DetHex()
    roster = load_roster(roster_path)
    shown = roster_path.relative_to(REPO) if roster_path.is_relative_to(REPO) else roster_path.name
    out.write("digital-twin team — offline chat-gateway demo (v0.2.0-alpha)\n")
    out.write("DEMO KEYS — public demo HMAC keys · mock adapter + mock driver · no network, no credentials\n")
    out.write("replies are canned: the mock driver matches keywords in fixtures/mock_driver.json, it is not a model\n")
    out.write(f"roster: {shown} (synthetic) · clock fixed at 2026-10-05 07:50 +08:00\n")
    if not (roster.get("_identities") or {}).get("users"):
        roster["_identities"] = json.loads(DEMO_IDENTITIES.read_text(encoding="utf-8"))
        out.write(f"identities: {DEMO_IDENTITIES.relative_to(REPO)} (synthetic mock users)\n")
    usages: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="mfg-team-demo-") as tmp:
        records: list[dict] = []
        audit = AuditLog(Path(tmp) / "audit", DEMO_AUDIT_KEY, clock=clock, on_append=records.append)
        driver = MockDriver()

        def on_note(note: dict) -> None:
            if "driver_mode" in note:
                driver.mode = note["driver_mode"]
            if "compact" in note:
                adapter.compact = bool(note["compact"])
            if note.get("sub"):
                out.write(f"  ({note['title'].strip('()')})\n")
            else:
                out.write(f"\n━━ Beat {note['beat']}/{BEATS} · {note['title']}\n")
            if note.get("refusal_checks"):
                refusal_checks(out, roster_path)

        adapter = MockAdapter(script=DEMO_SCRIPT, out=out, on_note=on_note, clock=clock)
        gw = Gateway(roster, adapter, driver, audit, clock, token_hex=hexgen,
                     approvals=ApprovalBook(DEMO_APPROVAL_KEY, clock=clock, token_hex=hexgen))
        out.write(f"gateway up: audit #{records[-1]['seq']} {records[-1]['action']}\n")
        for ev in adapter.events():
            clock.t = adapter.last_ts
            records.clear()
            for item in gw.handle(ev):
                adapter.post(item)
            trail = " → ".join(f"#{r['seq']} {r['action']}" + (f"({r['deny_reason']})" if r["deny_reason"] else "")
                               for r in records)
            out.write(f"    audit: {trail}\n")
            for r in records:
                if r["action"] == "msg_out" and r.get("usage"):
                    u = r["usage"]
                    usages.append(u)
                    out.write(f"    ≈ tokens in {u['input_tokens']:,} / out {u['output_tokens']:,}"
                              f" · est. US${u['cost_usd']:.4f}\n")
            if pace:
                time.sleep(pace)
        ok, n = verify(Path(tmp) / "audit", DEMO_AUDIT_KEY)
    out.write(f"\naudit verify: {'OK' if ok else 'FAILED'} ({n})\n")
    if usages:
        k = len(usages)
        tin = sum(u["input_tokens"] for u in usages) // k
        tout = sum(u["output_tokens"] for u in usages) // k
        cost = sum(u["cost_usd"] for u in usages) / k
        full = estimate_tokens("字" * (PROMPT_BUDGET_BYTES // 3))
        out.write(f"est. per answered message ({k}): in ≈{tin:,} / out ≈{tout:,} tokens ≈ US${cost:.4f}\n")
        out.write(f"  assumes US${ASSUMED_USD_PER_MTOK[0]:g}/US${ASSUMED_USD_PER_MTOK[1]:g} per MTok (an assumed price, "
                  f"not a quote; check current pricing) and small fixture prompts; a full {PROMPT_BUDGET_BYTES:,} B prompt adds up to "
                  f"≈{full:,} input tokens (≈US${full * ASSUMED_USD_PER_MTOK[0] / 1e6:.4f}).\n")
        out.write("  The claude-code driver bills the operator's account instead; each call is capped by "
                  "--max-budget-usd 0.10.\n")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", metavar="GOLDEN", help="compare the transcript with a golden file")
    ap.add_argument("--pace", type=float, default=0.0, help="seconds to sleep between events")
    ap.add_argument("--roster", type=Path, default=DEMO_ROSTER)
    args = ap.parse_args(argv)
    buf = io.StringIO()
    try:
        rc = run_demo(buf, args.roster.resolve(), args.pace)
    except ConfigRefused as exc:
        print(f"demo: refused to start (exit {exc.exit}): {exc}", file=sys.stderr)
        return exc.exit
    text = buf.getvalue()
    if args.check:
        golden = Path(args.check).read_text(encoding="utf-8")
        if golden != text:
            sys.stdout.writelines(difflib.unified_diff(golden.splitlines(True), text.splitlines(True),
                                                       "golden", "demo"))
            print("demo: transcript differs from golden", file=sys.stderr)
            return 1
        print(f"demo: transcript matches {args.check}")
        return rc
    sys.stdout.write(text)
    return rc


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
