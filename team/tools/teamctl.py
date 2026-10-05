#!/usr/bin/env python3
"""teamctl: validate, inspect and build the digital-twin team tier.

    teamctl.py [--repo-root DIR] check [--roster PATH] [--ci|--strict] [--today YYYY-MM-DD]
    teamctl.py roster [--roster PATH] [--json] [--crontab]
    teamctl.py audit-verify FILE_OR_DIR     (uses chat_gateway.audit.verify)
    teamctl.py build [build.py options]       (same as build.py)

`check` prints `::error file=PATH::E0xx: message` lines (CI annotation
format), then an outsource summary and a bytes / token-estimate table.
Default roster: team/local/roster.local.yaml if present, else the example;
`--ci` always defaults to the example.

Exit codes: 0 OK, 1 violations (E codes), 2 usage or IO error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _teamlib as lib  # noqa: E402


def _root(arg) -> Path:
    return Path(arg).resolve() if arg else lib.TOOL_REPO


def _roster_path(root: Path, arg, ci: bool) -> Path:
    return Path(arg) if arg else lib.default_roster(root, prefer_example=ci)


def cmd_check(args, root: Path) -> int:
    today = args.today or dt.date.today().isoformat()
    try:
        lib._date(today)
    except ValueError:
        print(f"teamctl: --today must be YYYY-MM-DD, got {today!r}",
              file=sys.stderr)
        return 2
    mode = "ci" if args.ci else "strict" if args.strict else "local"
    roster = _roster_path(root, args.roster, args.ci)
    try:
        findings, stats = lib.validate_ex(root, roster, mode=mode, today=today)
    except OSError as e:
        print(f"teamctl: cannot read {roster}: {e}", file=sys.stderr)
        return 2
    for f in findings:
        print(f.render())
    print(f"outsource: enabled {stats['outsource_enabled']} / "
          f"dormant {stats['outsource_dormant']}")
    rows = stats["budget_rows"]
    if rows:
        print("bytes budget (informational token estimate = CJK chars + other/4):")
        for label, n, limit, tok in rows:
            lim = f"{limit:,}" if limit else "-"
            t = f"~{tok:,} tok" if tok is not None else ""
            print(f"  {label:<58} {n:>7,} / {lim:>7}  {t}")
    errors = sum(1 for f in findings if f.severity == "error")
    warns = len(findings) - errors
    print(f"teamctl check [{mode}]: {'OK' if not errors else 'FAILED'} "
          f"({errors} errors, {warns} warnings)")
    return 1 if errors else 0


def cmd_roster(args, root: Path) -> int:
    roster_path = _roster_path(root, args.roster, False)
    try:
        findings = [f for f in lib.validate(root, roster_path, mode="local")
                    if f.severity == "error"]
        if findings:
            for f in findings:
                print(f.render(), file=sys.stderr)
            return 1
        c = lib.compile_all(root, roster_path)
    except OSError as e:
        print(f"teamctl: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(c.roster, sort_keys=True, ensure_ascii=False,
                         indent=2))
        return 0
    if args.crontab:
        data = lib.load_roster(roster_path)
        print("# example crontab lines (adjust paths; run as the service user)")
        for pos in data.get("positions", []):
            tw = pos.get("twin")
            if not (isinstance(tw, dict) and tw.get("enabled")):
                continue
            fm, _ = lib.load_twin(root / "team" / "twins" / f"{tw['file']}.md")
            for s in fm.get("schedule", []) or []:
                print(f"{s['cron']} cd {root} && PYTHONPATH=infra/chat-gateway "
                      f"python3 -m chat_gateway post --twin {tw['file']} "
                      f"--capability {s['capability']} --channel {s['channel']}")
        return 0
    sys.stdout.write(c.summary)
    return 0


def cmd_audit_verify(args, root: Path) -> int:
    gw = root / "infra" / "chat-gateway"
    sys.path.insert(0, str(gw))
    try:
        from chat_gateway import audit  # noqa: PLC0415
    except ImportError as e:
        print(f"teamctl: cannot import chat_gateway.audit ({e})",
              file=sys.stderr)
        return 2
    if not Path(args.file).exists():
        print(f"teamctl: no such file or directory {args.file}",
              file=sys.stderr)
        return 2
    ok, n = audit.verify(args.file)
    if ok:
        print(f"audit verify: OK ({n})")
        return 0
    print(f"audit verify: FAILED ({n} records verified before the break)")
    return 1


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo_root = None
    if len(argv) >= 2 and argv[0] == "--repo-root":
        repo_root, argv = argv[1], argv[2:]
    if argv and argv[0] == "build":
        import build  # noqa: PLC0415
        rest = argv[1:] + (["--repo-root", repo_root] if repo_root else [])
        return build.main(rest)
    ap = argparse.ArgumentParser(prog="teamctl", description=__doc__.split(
        "\n")[0])
    ap.add_argument("--repo-root", default=repo_root)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--roster")
    grp = c.add_mutually_exclusive_group()
    grp.add_argument("--ci", action="store_true")
    grp.add_argument("--strict", action="store_true")
    c.add_argument("--today")
    r = sub.add_parser("roster")
    r.add_argument("--roster")
    r.add_argument("--json", action="store_true")
    r.add_argument("--crontab", action="store_true")
    a = sub.add_parser("audit-verify")
    a.add_argument("file", metavar="FILE_OR_DIR")
    args = ap.parse_args(argv)
    root = _root(args.repo_root)
    try:
        return {"check": cmd_check, "roster": cmd_roster,
                "audit-verify": cmd_audit_verify}[args.cmd](args, root)
    except lib.LoadError as e:
        print(f"::error::{e.code}: {e.message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
