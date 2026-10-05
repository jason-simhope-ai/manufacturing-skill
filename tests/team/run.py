#!/usr/bin/env python3
"""Fixture runner for the team tooling (spec section 18, WP2; CI Step 19).

Reads tests/team/fixtures.yaml. Every `cases[]` entry is written into a mini
repo in a temp dir (the shared `base:` layer plus the case's own `files`,
`copy` and `replace` edits) and `team/tools/teamctl.py` runs against it; exit
code and the exact set of printed E/W codes must match `expect`. Every
`deid[]` entry runs `team/tools/deid.py` on a small CSV.

Usage:
    python3 tests/team/run.py [-v] [CASE_ID_SUBSTRING ...]

Exit 0 when every case passes, 1 otherwise.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TEAMCTL = REPO / "team" / "tools" / "teamctl.py"
DEID = REPO / "team" / "tools" / "deid.py"
FIXTURES = HERE / "fixtures.yaml"
DEFAULT_TODAY = "2026-10-05"
CODE_RE = re.compile(r"^::(?:error|warning) file=.*?::([EW]\d{3}):", re.M)


def placeholders() -> dict[str, str]:
    """Scanner-tripping samples are assembled here from fragments so no
    literal token, name or id appears in a tracked file."""
    return {
        "SLACK_TOKEN": "xo" + "xb-" + "1234567890-abcdefghijkl",
        "AWS_KEY": "AKI" + "AABCDEFGHIJKLMNOP",
        "EMAIL": "ops" + "@" + "acme-corp." + "net",
        "MOBILE": "09" + "12-345-" + "678",
        "SLACK_ID": "U0" + "ABCDEFG1",
        "DISCORD_ID": "12345678" + "9012345678",
        "ZH_NAME": "王" + "廠長",
        "HONORIFIC": "Mr" + ". " + "Smith",
    }


def expand(text: str) -> str:
    ph = placeholders()

    def sub(m):
        name, arg = m.group(1), m.group(2)
        if name == "PAD":
            return "x" * int(arg)
        if name == "GEN:CHANNELS":
            return "".join(
                f"  - {{ id: c{i:02d}, department: qa, tier: T1, "
                f"adapter: mock, twins: [qa-manager], defaultTwin: qa-manager,"
                f" autonomyCeiling: draft, askers: [qa-manager, chair-head] }}\n"
                for i in range(int(arg)))
        if name == "GEN:ALIASES":
            return ", ".join(f"alias-{i:02d}" for i in range(int(arg)))
        return ph[name]

    text = re.sub(r"@@(PAD|GEN:CHANNELS|GEN:ALIASES):(\d+)@@", sub, text)
    return re.sub(r"@@([A-Z_]+)@@", lambda m: ph[m.group(1)], text)


def write(root: Path, rel: str, content) -> None:
    p = root / rel
    if content is None:
        p.unlink(missing_ok=True)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(expand(content), encoding="utf-8")


def materialize(base: dict, case: dict, root: Path) -> None:
    for rel, content in base.items():
        write(root, rel, content)
    for dst, src in (case.get("copy") or {}).items():
        write(root, dst, (root / src).read_text(encoding="utf-8"))
    for rel, content in (case.get("files") or {}).items():
        write(root, rel, content)
    for rel, pairs in (case.get("replace") or {}).items():
        p = root / rel
        text = p.read_text(encoding="utf-8")
        for old, new in pairs:
            old, new = expand(old), expand(new)
            if old not in text:
                raise AssertionError(f"{case['id']}: {rel}: replace target "
                                     f"not found: {old!r}")
            text = text.replace(old, new, 1)
        p.write_text(text, encoding="utf-8")
    if case.get("git"):
        env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(root)}
        for cmd in (["git", "init", "-q"], ["git", "add", "-f", "-A"]):
            subprocess.run(cmd, cwd=root, check=True, env=env,
                           capture_output=True)


def run_case(base: dict, case: dict) -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="teamfx-") as tmp:
        root = Path(tmp)
        try:
            materialize(base, case, root)
        except AssertionError as e:
            return [str(e)]
        args = list(case["args"])
        if args and args[0] == "check" and "--today" not in args:
            args += ["--today", DEFAULT_TODAY]
        proc = subprocess.run(
            [sys.executable, str(TEAMCTL), "--repo-root", str(root), *args],
            capture_output=True, text=True, cwd=root)
        out = proc.stdout + proc.stderr
        exp = case["expect"]
        if proc.returncode != exp["exit"]:
            problems.append(f"exit {proc.returncode}, expected {exp['exit']}")
        got = set(CODE_RE.findall(out))
        want = set(exp.get("codes") or [])
        if got != want:
            problems.append(f"codes {sorted(got)}, expected {sorted(want)}")
        for s in exp.get("contains") or []:
            if s not in out:
                problems.append(f"output lacks {s!r}")
        if problems:
            problems.append("--- output ---\n" + out[-1500:])
    return problems


def run_deid_case(case: dict) -> list[str]:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="deidfx-") as tmp:
        root = Path(tmp)
        src, dst = root / "in.csv", root / "out.csv"
        mp = root / "deid-map.local.yaml"
        if case.get("input") is not None:
            src.write_text(expand(case["input"]), encoding="utf-8")
        if case.get("map") is not None:
            mp.write_text(case["map"], encoding="utf-8")
        if case.get("denylist") is not None:
            (root / "names.denylist").write_text(case["denylist"],
                                                 encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(DEID), "--in", str(src), "--out", str(dst),
             "--map", str(mp), *case.get("args", [])],
            capture_output=True, text=True, cwd=root)
        out = proc.stdout + proc.stderr
        exp = case["expect"]
        if proc.returncode != exp["exit"]:
            problems.append(f"exit {proc.returncode}, expected {exp['exit']}")
        if "output" in exp:
            got = dst.read_text(encoding="utf-8") if dst.exists() else None
            if got != exp["output"]:
                problems.append(f"output {got!r}, expected {exp['output']!r}")
        for s in exp.get("stdout") or []:
            if s not in out:
                problems.append(f"stdout lacks {s!r}")
        mtext = mp.read_text(encoding="utf-8") if mp.exists() else ""
        for s in exp.get("map") or []:
            if s not in mtext:
                problems.append(f"map lacks {s!r}")
        if problems:
            problems.append("--- output ---\n" + out[-800:])
    return problems


def load_fixtures() -> dict:
    return yaml.safe_load(FIXTURES.read_text(encoding="utf-8"))


def run_all(filters: tuple[str, ...] = (), verbose: bool = False
            ) -> tuple[int, list[str]]:
    data = load_fixtures()
    failures: list[str] = []
    total = 0
    for case in data["cases"]:
        if filters and not any(f in case["id"] for f in filters):
            continue
        total += 1
        problems = run_case(data["base"], case)
        if problems:
            failures.append(f"FAIL case {case['id']}: " + "; ".join(problems))
        elif verbose:
            print(f"ok   case {case['id']}")
    for case in data.get("deid") or []:
        if filters and not any(f in case["id"] for f in filters):
            continue
        total += 1
        problems = run_deid_case(case)
        if problems:
            failures.append(f"FAIL deid {case['id']}: " + "; ".join(problems))
        elif verbose:
            print(f"ok   deid {case['id']}")
    return total, failures


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    verbose = "-v" in argv
    filters = tuple(a for a in argv if a != "-v")
    total, failures = run_all(filters, verbose)
    for f in failures:
        print(f)
    print(f"team fixtures: {total - len(failures)}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
