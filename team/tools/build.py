#!/usr/bin/env python3
"""Compile a team roster into `team/.build/` (spec section 18, WP2).

    python3 team/tools/build.py [--roster PATH] [--out DIR] [--summary]
                                [--check-deterministic] [--repo-root DIR]

Writes roster.json, twins/<id>.prompt.md, ref/{agents,skills,know-how,hooks}/
<id>.md, and (only when local overlays exist) identities.json / bindings.json.
Default roster: team/local/roster.local.yaml, else team/roster.example.yaml
(demo mode, mock only). `--summary` prints a short summary (<= 1,200 B).

Exit codes: 0 OK, 1 violation, 2 usage or IO error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _teamlib as lib  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="build.py", description=__doc__.split(
        "\n")[0])
    ap.add_argument("--roster")
    ap.add_argument("--out")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--check-deterministic", action="store_true")
    ap.add_argument("--repo-root")
    ap.add_argument("--today", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else lib.TOOL_REPO
    roster = Path(args.roster) if args.roster else lib.default_roster(root)
    out = Path(args.out) if args.out else root / "team" / ".build"
    today = args.today
    try:
        if today:
            lib._date(today)
        findings = lib.validate(root, roster, mode="local", today=today)
        errors = [f for f in findings if f.severity == "error"]
        for f in findings:
            if f.severity == "error" or f.code in ("W006",):
                print(f.render(), file=sys.stderr)
        if errors:
            return 1
        if args.check_deterministic:
            bad = lib.check_deterministic(root, roster)
            for f in bad:
                print(f.render(), file=sys.stderr)
            if bad:
                return 1
        res = lib.build(root, roster, out)
    except lib.BuildError as e:
        for f in e.findings:
            print(f.render(), file=sys.stderr)
        return 1
    except lib.LoadError as e:
        print(f"::error file={roster}::{e.code}: {e.message}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as e:
        print(f"build.py: {e}", file=sys.stderr)
        return 2
    if args.summary:
        sys.stdout.write(res.summary)
    else:
        print(f"built {len(res.files)} files into {out} "
              f"(sourceHash {res.source_hash[:19]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
