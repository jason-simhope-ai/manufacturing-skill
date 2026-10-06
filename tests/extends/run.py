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

An optional `extra/` directory inside a case is copied verbatim into the
fake repo root (e.g. `extra/core-evil/agents/subject.md`) for cases that
need additional files. An optional `case.cfg` holds key=value overrides
(kind, profile, basename).

Runs all cases. Exit 0 on full pass; exit 1 on any failure. Also exits
non-zero when no cases are discovered, or when the discovered cases do not
exercise every directive type (canary: the suite cannot pass vacuously).
Error cases must exit non-zero with exactly one `::error` line and no
traceback.

Usage:
    python tests/extends/run.py
    python tests/extends/run.py --case case-01-pure-inherit  # one case
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
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
    extra = case_dir / "extra"
    if extra.is_dir():
        shutil.copytree(extra, dst, dirs_exist_ok=True)
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
    if not is_error_case and not (case_dir / "expected.md").exists():
        return False, (f"{name}: needs expected.md or expected_error.txt")
    for req in ("core.md", "profile.md"):
        if not (case_dir / req).exists():
            return False, f"{name}: missing {req}"

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
            if "Traceback" in proc.stderr:
                return False, (
                    f"{name}: error case crashed with a traceback "
                    f"instead of a clean error:\n{proc.stderr}"
                )
            n_err = sum(1 for ln in proc.stderr.splitlines()
                        if ln.startswith("::error"))
            if n_err != 1:
                return False, (
                    f"{name}: expected exactly one ::error line, got "
                    f"{n_err}:\n{proc.stderr}"
                )
            # `lint` (what CI runs) must agree with `resolve`.
            lint = subprocess.run(
                [sys.executable, str(RESOLVER), "--repo-root", str(tmp),
                 "lint", str(profile_path)],
                capture_output=True, text=True, timeout=15,
                encoding="utf-8", env=env,
            )
            if lint.returncode == 0:
                return False, f"{name}: `lint` passed but `resolve` failed"
            return True, f"{name}: ok (error {expected_err!r} matched)"

        # Success case
        if proc.returncode != 0:
            return False, (
                f"{name}: expected success but got exit "
                f"{proc.returncode}.\nstderr:\n{proc.stderr}"
            )
        lint = subprocess.run(
            [sys.executable, str(RESOLVER), "--repo-root", str(tmp),
             "lint", str(profile_path)],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", env=env,
        )
        if lint.returncode != 0:
            return False, (
                f"{name}: `resolve` passed but `lint` failed:\n"
                f"{lint.stderr}"
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


# Raw-text patterns (deliberately independent of the resolver's own
# scanner). Each directive type must appear in at least one success case.
CANARY_MARKERS = {
    "inherit": re.compile(r"<!--\s*inherit\s*-->"),
    "override-body": re.compile(r"<!--\s*override-body\s*-->"),
    "replace-section": re.compile(r"<!--\s*replace-section:"),
}


def canary(cases: list[Path]) -> list[str]:
    """Return problems if the suite would pass without covering a
    directive type or the error path."""
    problems = []
    success = [c for c in cases if (c / "expected.md").exists()]
    errors = [c for c in cases if (c / "expected_error.txt").exists()]
    for label, rx in CANARY_MARKERS.items():
        if not any(rx.search((c / "profile.md").read_text(encoding="utf-8"))
                   for c in success):
            problems.append(f"no success case exercises `{label}`")
    if not errors:
        problems.append("no error case (expected_error.txt) present")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", help="run a single case by directory name")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    cases = sorted(p for p in CASES_DIR.iterdir()
                   if p.is_dir() and p.name.startswith("case-"))
    if not cases:
        print(f"::error::no cases discovered under {CASES_DIR} "
              f"(expected case-*/ directories) — refusing to pass "
              f"vacuously", file=sys.stderr)
        print("0 cases discovered")
        return 1
    print(f"discovered {len(cases)} cases")
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            print(f"no case named {args.case!r}", file=sys.stderr)
            return 2
    else:
        problems = canary(cases)
        if problems:
            for pr in problems:
                print(f"::error::canary: {pr}", file=sys.stderr)
            return 1

    fail = 0
    for case_dir in cases:
        ok, msg = run_case(case_dir, args.verbose)
        symbol = "PASS" if ok else "FAIL"
        print(f"  {symbol}  {msg}")
        if not ok:
            fail += 1
    print(f"\n{len(cases) - fail}/{len(cases)} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
