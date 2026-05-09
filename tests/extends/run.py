#!/usr/bin/env python3
"""Golden-file test runner for the inheritance resolver.

Each case directory follows the convention:

    tests/extends/case-XX-<name>/
        core.md              # source-of-truth core file
        profile.md           # profile file with `extends:` etc.
        expected.md          # expected resolved output (success cases)
    OR
        core.md
        profile.md
        expected_error.txt   # substring that must appear in stderr

Runs all cases. Exit 0 on full pass; exit 1 with diff/diagnostic on
the first failure.

Usage:
    python tests/extends/run.py
    python tests/extends/run.py --case case-01-pure-inherit  # one case
"""
from __future__ import annotations

import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESOLVER = REPO_ROOT / "adapters" / "claude-code" / "_resolve_extends.py"
CASES_DIR = Path(__file__).resolve().parent


def build_fake_repo(case_dir: Path, dst: Path,
                    profile_kind: str = "agents",
                    profile_name: str = "test-profile",
                    file_basename: str = "subject") -> tuple[Path, str]:
    """Lay out a temp repo with the case's core.md and profile.md.

    Returns (profile_file_path, expected_extends_value).
    """
    core_dir = dst / "core" / profile_kind
    profile_dir = dst / "profiles" / profile_name / profile_kind
    core_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    core_src = case_dir / "core.md"
    profile_src = case_dir / "profile.md"
    core_dst = core_dir / f"{file_basename}.md"
    profile_dst = profile_dir / f"{file_basename}.md"

    shutil.copyfile(core_src, core_dst)
    shutil.copyfile(profile_src, profile_dst)
    return profile_dst, f"core/{profile_kind}/{file_basename}"


def run_case(case_dir: Path, verbose: bool = False) -> tuple[bool, str]:
    """Run a single case. Returns (ok, message)."""
    name = case_dir.name
    config = {}
    cfg_path = case_dir / "case.cfg"
    if cfg_path.exists():
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()

    is_error_case = (case_dir / "expected_error.txt").exists()

    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        kind = config.get("kind", "agents")
        profile_name = config.get("profile", "test-profile")
        basename = config.get("basename", "subject")
        profile_path, _ = build_fake_repo(
            case_dir, tmp, kind, profile_name, basename
        )

        cmd = [
            sys.executable, str(RESOLVER),
            "--repo-root", str(tmp),
            "resolve", str(profile_path),
        ]
        env = dict(os.environ, PYTHONIOENCODING="utf-8",
                   PYTHONUTF8="1")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15,
                encoding="utf-8", env=env,
            )
        except subprocess.TimeoutExpired:
            return False, f"{name}: TIMEOUT"

        if is_error_case:
            expected_err = (case_dir / "expected_error.txt").read_text(
                encoding="utf-8"
            ).strip()
            if proc.returncode == 0:
                return False, (
                    f"{name}: expected error containing {expected_err!r} "
                    f"but resolver succeeded with output:\n{proc.stdout}"
                )
            if expected_err not in proc.stderr:
                return False, (
                    f"{name}: error message did not contain "
                    f"{expected_err!r}.\nGot stderr:\n{proc.stderr}"
                )
            return True, f"{name}: ok (error {expected_err!r} matched)"

        # Success case
        if proc.returncode != 0:
            return False, (
                f"{name}: expected success but got exit "
                f"{proc.returncode}.\nstderr:\n{proc.stderr}"
            )
        expected = (case_dir / "expected.md").read_text(encoding="utf-8")
        actual = proc.stdout
        if normalize(actual) != normalize(expected):
            diff = "\n".join(difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=f"{name}/expected.md",
                tofile=f"{name}/actual",
                lineterm="",
            ))
            return False, f"{name}: output mismatch\n{diff}"
        return True, f"{name}: ok"


def normalize(s: str) -> str:
    """Compare ignoring trailing whitespace and final newlines."""
    return "\n".join(line.rstrip() for line in s.splitlines()).rstrip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="run a single case by directory name")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    cases = sorted(p for p in CASES_DIR.iterdir()
                   if p.is_dir() and p.name.startswith("case-"))
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            print(f"no case named {args.case!r}", file=sys.stderr)
            return 2

    fail = 0
    for case_dir in cases:
        ok, msg = run_case(case_dir, args.verbose)
        symbol = "PASS" if ok else "FAIL"
        print(f"  {symbol}  {msg}" if ok else f"  {symbol}  {msg}")
        if not ok:
            fail += 1
    print(f"\n{len(cases) - fail}/{len(cases)} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
