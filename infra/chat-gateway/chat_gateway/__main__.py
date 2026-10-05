"""CLI: `PYTHONPATH=infra/chat-gateway python3 -m chat_gateway <command>`.

    run          [--roster P] [--adapter mock|slack|discord] [--driver mock|claude-code] [--script F.jsonl] [--pace S]
    post         --twin ID --capability ID [--channel ID] [--roster P] [--adapter …] [--driver …]
    audit-verify FILE_OR_DIR
    self-check   [--roster P] [--adapter …] [--driver …]

Exit: 0 OK · 3 T3 refused · 64 usage · 70 internal · 78 config refused.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Mapping, Sequence

from . import EXIT_CONFIG, EXIT_INTERNAL, EXIT_OK, EXIT_USAGE, ConfigRefused
from .adapters import load_adapter_class
from .adapters.base import ApprovalCard, ScheduledPost
from .adapters.mock import MockAdapter
from .approvals import ApprovalBook
from .audit import AuditLog, heads, verify_report
from .config import AUDIT_KEY_VAR, DEMO_AUDIT_KEY, GatewayConfig, config_from_env, stale_state_help
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


def _make_driver(cfg: GatewayConfig, env: Mapping[str, str]):
    cls = load_driver_class(cfg.driver)
    if cfg.driver == "mock":
        return cls()
    if not env.get("MFG_TEAM_CLAUDE_CONFIG_DIR"):
        raise ConfigRefused("missing required environment variables: MFG_TEAM_CLAUDE_CONFIG_DIR")
    return cls(bin=env.get("MFG_TEAM_CLAUDE_BIN", "claude"), config_dir=env["MFG_TEAM_CLAUDE_CONFIG_DIR"],
               max_budget_usd=cfg.max_budget_usd, timeout_s=cfg.timeout_s,
               data_root=env.get("MFG_TEAM_DATA_T1") or None)


def build_gateway(cfg: GatewayConfig, env: Mapping[str, str], script: str | None = None) -> Gateway:
    roster = load_roster(cfg.roster)
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
    adapter = _make_adapter(cfg, roster, script)
    driver = _make_driver(cfg, env)
    try:
        audit = AuditLog(cfg.state_dir / "audit", cfg.audit_key)
    except ConfigRefused as exc:
        raise ConfigRefused(str(exc) + stale_state_help(cfg.state_dir, env), exc.exit) from None
    data_root = env.get("MFG_TEAM_DATA_T1")
    return Gateway(roster, adapter, driver, audit, approvals=ApprovalBook(cfg.approval_key),
                   read_roots=(data_root,) if data_root else (), daily_budget_usd=cfg.daily_budget_usd,
                   max_budget_usd=cfg.max_budget_usd, timeout_s=cfg.timeout_s, extra_dlp=extra_dlp)


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
    for out in outs:
        (gw.adapter.post_approval if isinstance(out, ApprovalCard) else gw.adapter.post)(out)
    if not outs:
        print("post refused by policy (see audit log)", file=sys.stderr)
    return EXIT_OK


def audit_key_for_verify(env: Mapping[str, str]) -> bytes:
    """The audit key from the environment, else the public demo key (with a notice)."""
    if env.get(AUDIT_KEY_VAR):
        return env[AUDIT_KEY_VAR].encode()
    print(f"DEMO KEY — {AUDIT_KEY_VAR} is not set; verifying with the public demo key "
          "(only mock-mode logs will verify)", file=sys.stderr)
    return DEMO_AUDIT_KEY


def print_verify(path: str, key: bytes) -> bool:
    ok, n, problems = verify_report(path, key)
    print(f"audit verify: {'OK' if ok else 'FAILED'} ({n})")
    for problem in problems[:20]:
        print(f"  problem: {problem}")
    info = heads(path, key) if ok else None
    if info:
        print(f"  last seq {info['seq']}; checkpoint heads (copy off-host for sign-off):")
        for tier, h in sorted(info["tiers"].items()):
            print(f"    {tier}: count={h['count']} seq={h['seq']} head={h['head']}")
    return ok


def _audit_verify(path: str, env: Mapping[str, str]) -> int:
    return EXIT_OK if print_verify(path, audit_key_for_verify(env)) else EXIT_CONFIG


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
    sub.add_parser("audit-verify").add_argument("path")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_USAGE
    try:
        if args.cmd == "audit-verify":
            if not Path(args.path).exists():
                print(f"no such file: {args.path}", file=sys.stderr)
                return EXIT_USAGE
            return _audit_verify(args.path, env)
        cfg = config_from_env(env, roster=args.roster, adapter=args.adapter, driver=args.driver)
        gw = build_gateway(cfg, env, getattr(args, "script", None))
        if args.cmd == "self-check":
            print("self-check: OK")
            return EXIT_OK
        if args.cmd == "post":
            return _post(gw, cfg, args.twin, args.capability, args.channel)
        gw.run(pace=args.pace)
        return EXIT_OK
    except ConfigRefused as exc:
        print(f"chat_gateway: refused to start (exit {exc.exit}): {exc}", file=sys.stderr)
        return exc.exit
    except (ValueError, ImportError) as exc:
        print(f"chat_gateway: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:  # noqa: BLE001
        print(f"chat_gateway: internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
