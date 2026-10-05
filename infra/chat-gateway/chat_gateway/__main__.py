"""CLI: `PYTHONPATH=infra/chat-gateway python3 -m chat_gateway <command>`.

    run          [--roster P] [--adapter mock|slack|discord] [--driver mock|claude-code] [--script F.jsonl] [--pace S]
    post         --twin ID --capability ID [--channel ID] [--roster P] [--adapter …] [--driver …]
    audit-verify FILE_OR_DIR [--heads-out FILE] [--anchor FILE]
    self-check   [--roster P] [--adapter …] [--driver …]
    freeze | unfreeze                       (kill switch: flag file in the state dir)

Exit: 0 OK · 3 T3 refused · 64 usage · 65 bad script line · 70 internal · 78 config refused.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence

from . import EXIT_CONFIG, EXIT_DATA, EXIT_INTERNAL, EXIT_OK, EXIT_USAGE, ConfigRefused, UsageError
from .adapters import load_adapter_class
from .adapters.base import ScheduledPost
from .adapters.mock import MockAdapter, ScriptError
from .approvals import ApprovalBook
from .audit import (AuditLog, action_totals, check_anchor, counts, foreign_key_chain, heads, heads_document, newer_heads,
                    verify_report, write_heads)
from .config import (AUDIT_KEY_VAR, DEMO_AUDIT_KEY, DENYLIST_VAR, FREEZE_FILE, FREEZE_LAST, NO_DENYLIST_VAR,
                     STATE_DIR_VAR, GatewayConfig, config_from_env, ensure_state_dir, resolve_state_dir,
                     stale_state_help)
from .core import Gateway, load_roster, synthetic_mock_identities
from .sanitize import load_denylist
from .drivers import load_driver_class


def _make_adapter(cfg: GatewayConfig, roster: dict, script: str | None):
    if cfg.adapter == "mock":
        return MockAdapter(script=script)
    try:
        cls = load_adapter_class(cfg.adapter)
    except ImportError as exc:
        raise ConfigRefused(f"adapter {cfg.adapter} unavailable ({exc.name} not installed)") from None
    return cls(bindings=roster.get("_bindings") or {})


def _make_driver(cfg: GatewayConfig, env: Mapping[str, str], extra_dlp=()):
    cls = load_driver_class(cfg.driver)
    if cfg.driver == "mock":
        return cls()
    if not env.get("MFG_TEAM_CLAUDE_CONFIG_DIR"):
        raise ConfigRefused("missing required environment variables: MFG_TEAM_CLAUDE_CONFIG_DIR")
    return cls(bin=env.get("MFG_TEAM_CLAUDE_BIN", "claude"), config_dir=env["MFG_TEAM_CLAUDE_CONFIG_DIR"],
               max_budget_usd=cfg.max_budget_usd, timeout_s=cfg.timeout_s,
               data_root=env.get("MFG_TEAM_DATA_T1") or None, state_dir=cfg.state_dir, env=env,
               extra_dlp=extra_dlp)


def build_gateway(cfg: GatewayConfig, env: Mapping[str, str], script: str | None = None) -> Gateway:
    roster = load_roster(cfg.roster)
    ensure_state_dir(cfg.state_dir)
    if cfg.demo_keys:
        print("DEMO KEYS — mock mode only; set MFG_TEAM_AUDIT_HMAC_KEY and "
              "MFG_TEAM_APPROVAL_HMAC_KEY for anything real", file=sys.stderr)
    if cfg.adapter == "mock" and cfg.driver == "mock" and not (roster.get("_identities") or {}).get("users"):
        roster["_identities"] = synthetic_mock_identities(roster)
        users = ", ".join(u["userId"] for u in roster["_identities"]["users"])
        print(f"no identities.json: mock mode uses synthetic users ({users})", file=sys.stderr)
    try:
        extra_dlp = load_denylist(cfg.denylist) if cfg.denylist else []
    except (OSError, ValueError) as exc:
        raise ConfigRefused(f"local denylist unusable: {exc}") from None
    deny_info = {"path": str(cfg.denylist) if cfg.denylist else None, "entries": len(extra_dlp)}
    adapter = _make_adapter(cfg, roster, script)
    if cfg.adapter != "mock" and not extra_dlp and not cfg.no_denylist:
        # I05: on a real chat platform the local denylist (customer / project / drawing names) catches
        # what the built-in patterns cannot; running without one must be an explicit choice.
        what = f"local denylist {cfg.denylist} has no entries" if cfg.denylist else "no local denylist"
        raise ConfigRefused(f"{what}: set {DENYLIST_VAR} to the denylist file (seed it from "
                            f"team/tools/denylist.starter.txt), or set {NO_DENYLIST_VAR}=1 to run without one "
                            "on purpose", exit=EXIT_USAGE)
    driver = _make_driver(cfg, env, extra_dlp)
    if cfg.driver == "mock":
        print("mock driver: replies are canned keyword matches from fixtures/mock_driver.json, "
              "not model output", file=sys.stderr)
    # Replay: the script's own `ts` is the gateway clock, so rate limits and dedupe follow script time.
    clock = adapter.replay_clock if isinstance(adapter, MockAdapter) and script else time.time
    try:
        audit = AuditLog(cfg.state_dir / "audit", cfg.audit_key, clock=clock)
    except ConfigRefused as exc:
        root = cfg.state_dir / "audit"
        if foreign_key_chain(root, cfg.audit_key):
            # I04: every record and the checkpoint fail under this key, so the chain was started under
            # another key (typically a mock rehearsal with the public demo key). Not a tamper signal.
            which = ("the public demo key (a mock rehearsal)" if cfg.audit_key != DEMO_AUDIT_KEY
                     and verify_report(root, DEMO_AUDIT_KEY)[0] else "a different key")
            raise ConfigRefused(
                f"the audit chain in {root} was started under {which}, not the key now configured: "
                f"archive {root} and start a new chain (docs/audit-operations.md §3, steps 3–5). No record "
                "verifies under this key, so this is a key mismatch, not by itself a sign of tampering. Run "
                f"mock rehearsals with a separate {STATE_DIR_VAR}" + stale_state_help(cfg.state_dir, env, foreign_key=True),
                exc.exit) from None
        raise ConfigRefused(str(exc) + stale_state_help(cfg.state_dir, env), exc.exit) from None
    data_root = env.get("MFG_TEAM_DATA_T1")
    return Gateway(roster, adapter, driver, audit, clock, approvals=ApprovalBook(cfg.approval_key, clock=clock),
                   read_roots=(data_root,) if data_root else (), daily_budget_usd=cfg.daily_budget_usd,
                   max_budget_usd=cfg.max_budget_usd, timeout_s=cfg.timeout_s, extra_dlp=extra_dlp,
                   frozen_flag=cfg.state_dir / FREEZE_FILE, config_info={"denylist": deny_info})


def _post(gw: Gateway, cfg: GatewayConfig, twin: str, capability: str, channel: str | None) -> int:
    t = gw.twins.get(twin)
    if t is None:
        print(f"unknown twin {twin!r}", file=sys.stderr)
        return EXIT_USAGE
    channel = channel or (t.get("channels") or [""])[0]
    state = cfg.state_dir / "post-limits.json"
    if state.is_file():
        gw.post_rl.load(json.loads(state.read_text(encoding="utf-8")))
    outs = gw.handle(ScheduledPost(twin, capability, channel))
    state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.write_text(json.dumps(gw.post_rl.dump()), encoding="utf-8")
    failed = sum(not gw.deliver(out) for out in outs)
    if not outs:
        print("post refused by policy (see audit log)", file=sys.stderr)
    if failed:
        print(f"post failed on the chat platform ({failed} message(s); see audit log, action post_failed)",
              file=sys.stderr)
        return EXIT_INTERNAL
    return EXIT_OK


def audit_key_for_verify(env: Mapping[str, str]) -> bytes:
    """The audit key from the environment, else the public demo key (with a notice)."""
    if env.get(AUDIT_KEY_VAR):
        return env[AUDIT_KEY_VAR].encode()
    print(f"DEMO KEY — {AUDIT_KEY_VAR} is not set; verifying with the public demo key "
          "(only mock-mode logs will verify)", file=sys.stderr)
    return DEMO_AUDIT_KEY


def print_verify(path: str, key: bytes, heads_out: str | None = None, anchor: str | None = None) -> bool:
    """Verify, then optionally compare with an earlier off-host heads file (`anchor`) and write the
    current heads (`heads_out`, only when everything verified). Returns overall success."""
    ok, n, problems = verify_report(path, key)
    anchor_doc = None
    if anchor is not None:
        try:
            anchor_doc = json.loads(Path(anchor).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems = problems + [f"anchor {anchor} unreadable ({type(exc).__name__})"]
        else:
            problems = problems + (check_anchor(path, key, anchor_doc) if ok else [])
            # P-09: a validly signed heads file newer than the anchor next to it or next to --heads-out
            # means the anchor is stale (e.g. latest.json rolled back together with the log).
            dirs = [Path(anchor).parent] + ([Path(heads_out).parent] if heads_out else [])
            problems = problems + newer_heads(dirs, key, anchor_doc,
                                              exclude=[Path(anchor)] + ([Path(heads_out)] if heads_out else []))
        ok = not problems
    print(f"audit verify: {'OK' if ok else 'FAILED'} ({n})")
    for problem in problems[:20]:
        print(f"  problem: {problem}")
    info = heads(path, key) if ok else None
    if info:
        print(f"  last seq {info['seq']}; checkpoint heads (copy off-host for sign-off):")
        for tier, h in sorted(info["tiers"].items()):
            print(f"    {tier}: count={h['count']} seq={h['seq']} head={h['head']}")
    if ok and anchor_doc is not None:
        print(f"  anchor: OK — no tier went backwards since {anchor_doc.get('created')} (seq {anchor_doc.get('seq')})")
    if ok:
        totals = action_totals(path, key)
        shown = " ".join(f"{a}={n}" for a, n in totals.items())
        print(f"  deny events (all tier files, for the weekly sign-off): {shown}")
    # Output is per tier and per channel/capability only, never per user (team README "給主管").
    for action, by_where in sorted((counts(path, key) if ok else {}).items()):
        shown = ", ".join(f"{w}={n}" for w, n in sorted(by_where.items()))
        print(f"  {action} (count only, no per-person breakdown): {shown}")
    if ok and heads_out:
        doc = heads_document(path, key)
        if doc is None:
            return False
        try:
            write_heads(doc, heads_out)
        except OSError as exc:
            print(f"  problem: cannot write {heads_out} ({type(exc).__name__})")
            return False
        print(f"  heads written to {heads_out} (copy it off-host; use it as --anchor next time)")
    return ok


def _audit_verify(path: str, env: Mapping[str, str], heads_out: str | None = None, anchor: str | None = None) -> int:
    return EXIT_OK if print_verify(path, audit_key_for_verify(env), heads_out, anchor) else EXIT_CONFIG


def _freeze(env: Mapping[str, str], on: bool) -> int:
    """S03 kill switch. `freeze` writes `<state dir>/frozen`; a running gateway checks it before every
    event and answers 「分身暫停服務中」 without calling the model. `unfreeze` renames it to
    `frozen.last` (its mtime marks when the freeze began: approval cards issued before it stay void).
    P-05: both refuse (exit 78) unless the state directory already exists with the expected owner and
    mode; they never create it, so a wrong user or path cannot report a freeze that does nothing."""
    state = resolve_state_dir(env)
    if state.is_symlink():
        raise ConfigRefused(f"state directory {state} is a symlink; set {STATE_DIR_VAR} to the real directory")
    ensure_state_dir(state, create=False)
    real = Path(os.path.realpath(state))
    if not (real / "audit").is_dir():
        raise ConfigRefused(f"state directory {real} holds no audit/ directory: this is not the state directory "
                            f"of a gateway that has run; check {STATE_DIR_VAR} and the user")
    flag = real / FREEZE_FILE
    if on:
        fd = os.open(flag, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
        print(f"frozen: {flag} written. A running gateway answers 「分身暫停服務中」 from its next event on "
              "(audit action `frozen`), drops replies still in flight and voids pending approval cards. To cut "
              "access completely, also stop the service and revoke the tokens (infra/chat-gateway/RUNBOOK.md).")
        return EXIT_OK
    if not os.path.lexists(flag):
        print(f"unfreeze: {flag} not present; the gateway was not frozen")
        return EXIT_OK
    os.replace(flag, real / FREEZE_LAST)
    print(f"unfrozen: {flag} moved to {FREEZE_LAST}; the gateway serves again from its next event "
          "(approval cards issued before the freeze stay void)")
    return EXIT_OK


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(prog="chat_gateway")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "post", "self-check"):
        p = sub.add_parser(name)
        p.add_argument("--roster")
        p.add_argument("--adapter", choices=("mock", "slack", "discord"))
        p.add_argument("--driver", choices=("mock", "claude-code"))
        if name == "run":
            p.add_argument("--script")
            p.add_argument("--pace", type=float, default=0.0)
        if name == "post":
            p.add_argument("--twin", required=True)
            p.add_argument("--capability", required=True)
            p.add_argument("--channel")
    av = sub.add_parser("audit-verify")
    av.add_argument("path")
    av.add_argument("--heads-out", metavar="FILE")
    av.add_argument("--anchor", metavar="FILE")
    sub.add_parser("freeze")
    sub.add_parser("unfreeze")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_USAGE
    try:
        if args.cmd == "audit-verify":
            if not Path(args.path).exists():
                print(f"no such file: {args.path}", file=sys.stderr)
                return EXIT_USAGE
            return _audit_verify(args.path, env, args.heads_out, args.anchor)
        if args.cmd in ("freeze", "unfreeze"):
            return _freeze(env, args.cmd == "freeze")
        cfg = config_from_env(env, roster=args.roster, adapter=args.adapter, driver=args.driver)
        had_chain = (cfg.state_dir / "audit" / "checkpoint.json").exists()
        gw = build_gateway(cfg, env, getattr(args, "script", None))
        if gw.frozen():
            print(f"FROZEN: {gw.frozen_flag} exists; every event is answered 「分身暫停服務中」 until "
                  "`python3 -m chat_gateway unfreeze`", file=sys.stderr)
        if args.cmd == "self-check":
            deny = (gw.config_info.get("denylist") or {})
            print(f"self-check: denylist: {deny.get('path')} ({deny.get('entries', 0)} entries)" if deny.get("entries")
                  else f"self-check: denylist: NOT LOADED (set {DENYLIST_VAR}"
                       + (f"; {NO_DENYLIST_VAR}=1 is set)" if cfg.no_denylist else ")"))
            if had_chain:
                print(f"self-check: note: {cfg.state_dir / 'audit'} already held an audit chain; this check "
                      f"appended to it (now seq {gw.audit.next_seq - 1})", file=sys.stderr)
            if cfg.demo_keys:
                print(f"self-check: warning: DEMO KEYS wrote to {cfg.state_dir / 'audit'}; never point a real "
                      f"deployment at this directory (use a separate {STATE_DIR_VAR} for rehearsals)",
                      file=sys.stderr)
            print("self-check: OK" + (" (frozen)" if gw.frozen() else ""))
            return EXIT_OK
        if args.cmd == "post":
            return _post(gw, cfg, args.twin, args.capability, args.channel)
        gw.run(pace=args.pace)
        return EXIT_OK
    except ConfigRefused as exc:
        print(f"chat_gateway: refused to start (exit {exc.exit}): {exc}", file=sys.stderr)
        return exc.exit
    except ScriptError as exc:
        print(f"chat_gateway: {exc}", file=sys.stderr)
        return EXIT_DATA
    except UsageError as exc:                        # our own wording (unknown name, missing script)
        print(f"chat_gateway: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except (ValueError, ImportError) as exc:
        # R-02 (EXT-15): class name only; an SDK or transport ValueError can carry URLs or request data.
        print(f"chat_gateway: {type(exc).__name__}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001
        # EXT-15: class name only. An SDK exception's text can carry request context (ids, URLs).
        print(f"chat_gateway: internal error: {type(exc).__name__}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
