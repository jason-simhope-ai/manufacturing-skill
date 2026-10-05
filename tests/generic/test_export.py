#!/usr/bin/env python3
"""Tests for the generic markdown export adapter.

Runs `adapters/generic/export.py` end-to-end (subprocess) against the
real repo and against synthetic mini-repos built in temp dirs.

Usage:
    python3 tests/generic/test_export.py        # exits non-zero on failure
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPORT = REPO_ROOT / "adapters" / "generic" / "export.py"
EXTENDS_CASES = REPO_ROOT / "tests" / "extends"
KINDS = ("agents", "skills", "know-how", "hooks", "commands")
OVERLAY_KINDS = ("agents", "skills", "know-how", "hooks")


def run_export(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    return subprocess.run(
        [sys.executable, str(EXPORT), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
        timeout=60,
    )


def exported_set(out: Path) -> set[str]:
    return {
        p.relative_to(out).as_posix()
        for k in KINDS if (out / k).is_dir()
        for p in (out / k).glob("*.md")
    }


def normalize(s: str) -> str:
    """Same normalization as tests/extends/run.py."""
    return "\n".join(line.rstrip() for line in s.splitlines()).rstrip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_fake_repo(root: Path, core: dict, profiles: dict) -> Path:
    """core = {"agents/foo.md": text}; profiles = {"alpha": {...}}."""
    write(root / "plugin.json", json.dumps({
        "name": "manufacturing-skill", "version": "9.9.9",
        "profiles": {"available": sorted(profiles)},
    }))
    for rel, text in core.items():
        write(root / "core" / rel, text)
    for name, files in profiles.items():
        write(root / "profiles" / name / "profile.json", json.dumps({
            "name": name, "displayName": name.upper(), "version": "1.2.3",
        }))
        for rel, text in files.items():
            write(root / "profiles" / name / rel, text)
    return root


class GenericExportTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def assertExportOk(self, proc):
        self.assertEqual(proc.returncode, 0,
                         f"export failed:\n{proc.stdout}\n{proc.stderr}")

    def assertOneLineError(self, proc, needle: str):
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        lines = [ln for ln in proc.stderr.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, f"want one-line error: {lines}")
        self.assertTrue(lines[0].startswith("error: "), lines[0])
        self.assertIn(needle, lines[0])

    # ---- file sets on the real repo ----

    def test_core_only_file_set(self):
        out = self.tmp / "out"
        self.assertExportOk(run_export("--core-only", "--out", str(out),
                                       "--reproducible"))
        expected = {
            f"{k}/{p.name}" for k in KINDS
            for p in (REPO_ROOT / "core" / k).glob("*.md")
        }
        self.assertTrue(expected)
        self.assertEqual(exported_set(out), expected)
        manifest = json.loads((out / "MANIFEST.json").read_text("utf-8"))
        self.assertEqual(manifest["profiles"], [])
        self.assertTrue(all(f["origin"] == "core" for f in manifest["files"]))

    def test_single_profile_file_set(self):
        out = self.tmp / "out"
        self.assertExportOk(run_export("--profiles", "cnc-machining",
                                       "--out", str(out), "--reproducible"))
        expected = {
            f"{k}/{p.name}" for k in KINDS
            for p in (REPO_ROOT / "core" / k).glob("*.md")
        }
        prof = REPO_ROOT / "profiles" / "cnc-machining"
        prof_files = {
            f"{k}/{p.name}" for k in OVERLAY_KINDS
            for p in (prof / k).glob("*.md") if not p.name.startswith("_")
        }
        self.assertTrue(prof_files)
        self.assertEqual(exported_set(out), expected | prof_files)
        manifest = json.loads((out / "MANIFEST.json").read_text("utf-8"))
        self.assertEqual([p["name"] for p in manifest["profiles"]],
                         ["cnc-machining"])
        self.assertEqual(manifest["pluginVersion"], json.loads(
            (REPO_ROOT / "plugin.json").read_text("utf-8"))["version"])
        by_path = {f["path"]: f for f in manifest["files"]}
        for rel in prof_files:
            self.assertEqual(by_path[rel]["profile"], "cnc-machining")

    def test_include_filter_and_platform_notes(self):
        out = self.tmp / "out"
        self.assertExportOk(run_export("--core-only", "--out", str(out),
                                       "--include", "commands,hooks"))
        self.assertEqual({p.split("/")[0] for p in exported_set(out)},
                         {"commands", "hooks"})
        quote = (out / "commands" / "quote.md").read_text("utf-8")
        self.assertTrue(quote.startswith("---\n"))
        self.assertIn("Claude Code specific", quote)
        hook = (out / "hooks" / "pre-quote.md").read_text("utf-8")
        self.assertIn("Documentation only", hook)
        manifest = json.loads((out / "MANIFEST.json").read_text("utf-8"))
        self.assertIn("generatedAt", manifest)  # not --reproducible

    def test_unknown_include_kind_exits_nonzero(self):
        proc = run_export("--core-only", "--out", str(self.tmp / "x"),
                          "--include", "agents,mcp")
        self.assertOneLineError(proc, "--include")

    # ---- overlay semantics on a synthetic repo ----

    def test_profile_override_wins_over_core(self):
        repo = make_fake_repo(self.tmp / "repo", core={
            "agents/foo.md": "---\nname: foo\n---\n\nCORE BODY\n",
            "agents/bar.md": "---\nname: bar\n---\n\nCORE BAR\n",
        }, profiles={"alpha": {
            "agents/foo.md": "---\nname: foo\n---\n\nPROFILE BODY\n",
            "agents/_stub.md": "template, never exported\n",
        }})
        out = self.tmp / "out"
        self.assertExportOk(run_export("--repo-root", str(repo),
                                       "--profiles", "alpha",
                                       "--out", str(out)))
        self.assertEqual(exported_set(out), {"agents/foo.md",
                                             "agents/bar.md"})
        foo = (out / "agents" / "foo.md").read_text("utf-8")
        self.assertIn("PROFILE BODY", foo)
        self.assertNotIn("CORE BODY", foo)
        manifest = json.loads((out / "MANIFEST.json").read_text("utf-8"))
        by_path = {f["path"]: f for f in manifest["files"]}
        self.assertEqual(by_path["agents/foo.md"]["origin"], "profile")
        self.assertEqual(by_path["agents/bar.md"]["origin"], "core")

    def test_extends_matches_resolver_fixtures(self):
        """Every success case under tests/extends/ must export to exactly
        the resolver's expected.md (same normalization as run.py)."""
        cases = sorted(
            p for p in EXTENDS_CASES.iterdir()
            if p.is_dir() and (p / "expected.md").is_file()
            and not (p / "case.cfg").exists()
        )
        self.assertTrue(cases)
        for case in cases:
            with self.subTest(case=case.name):
                repo = make_fake_repo(
                    self.tmp / case.name / "repo",
                    core={"agents/subject.md":
                          (case / "core.md").read_text("utf-8")},
                    profiles={"test-profile": {
                        "agents/subject.md":
                            (case / "profile.md").read_text("utf-8")}},
                )
                out = self.tmp / case.name / "out"
                self.assertExportOk(run_export(
                    "--repo-root", str(repo), "--profiles", "test-profile",
                    "--out", str(out), "--include", "agents"))
                actual = (out / "agents" / "subject.md").read_text("utf-8")
                expected = (case / "expected.md").read_text("utf-8")
                self.assertEqual(normalize(actual), normalize(expected))
                manifest = json.loads(
                    (out / "MANIFEST.json").read_text("utf-8"))
                self.assertEqual(manifest["files"][0]["origin"],
                                 "profile+extends")
                self.assertEqual(manifest["files"][0]["extends"],
                                 "core/agents/subject.md")

    def test_extends_resolver_failure_exits_nonzero(self):
        case = EXTENDS_CASES / "case-10-error-bad-extends-path"
        repo = make_fake_repo(self.tmp / "repo", core={
            "agents/subject.md": (case / "core.md").read_text("utf-8"),
        }, profiles={"test-profile": {
            "agents/subject.md": (case / "profile.md").read_text("utf-8"),
        }})
        proc = run_export("--repo-root", str(repo), "--profiles",
                          "test-profile", "--out", str(self.tmp / "out"))
        self.assertOneLineError(proc, "extends resolve failed")

    # ---- determinism + manifest integrity ----

    def test_bundle_deterministic(self):
        for profiles in ("cnc-machining", "cnc-machining,injection-molding"):
            with self.subTest(profiles=profiles):
                a, b = self.tmp / f"a-{profiles}", self.tmp / f"b-{profiles}"
                for out in (a, b):
                    self.assertExportOk(run_export(
                        "--profiles", profiles, "--out", str(out),
                        "--format", "bundle", "--reproducible"))
                name = ("manufacturing-skill."
                        f"{profiles.replace(',', '+')}.md")
                self.assertEqual([p.name for p in a.iterdir()], [name])
                data = (a / name).read_bytes()
                self.assertEqual(data, (b / name).read_bytes())
                text = data.decode("utf-8")
                self.assertIn("## 目錄 / Table of contents", text)
                self.assertIn("How to use this with any LLM agent", text)
                self.assertIn('<a id="agents--quote-specialist"></a>', text)
                self.assertIn("| name | quote |", text)
                self.assertIn("Claude Code specific", text)

    def test_files_reproducible_and_manifest_hashes(self):
        a, b = self.tmp / "a", self.tmp / "b"
        for out in (a, b):
            self.assertExportOk(run_export(
                "--profiles", "cnc-machining,injection-molding",
                "--out", str(out), "--reproducible"))
        ma = (a / "MANIFEST.json").read_bytes()
        self.assertEqual(ma, (b / "MANIFEST.json").read_bytes())
        manifest = json.loads(ma)
        self.assertNotIn("generatedAt", manifest)
        self.assertEqual({f["path"] for f in manifest["files"]},
                         exported_set(a))
        for f in manifest["files"]:
            data = (a / f["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), f["sha256"],
                             f["path"])
            self.assertEqual(len(data), f["bytes"], f["path"])

    def test_refuses_to_overwrite_without_force(self):
        out = self.tmp / "out"
        self.assertExportOk(run_export("--core-only", "--out", str(out)))
        stray = out / "agents" / "stale.md"
        stray.write_text("stale", encoding="utf-8")
        self.assertOneLineError(
            run_export("--core-only", "--out", str(out)), "--force")
        self.assertExportOk(run_export("--core-only", "--out", str(out),
                                       "--force"))
        self.assertFalse(stray.exists())

    # ---- failure modes ----

    def test_conflicting_profiles_exit_nonzero(self):
        repo = make_fake_repo(self.tmp / "repo", core={}, profiles={
            "alpha": {"agents/foo.md": "---\nname: foo\n---\nA\n"},
            "beta": {"agents/foo.md": "---\nname: foo\n---\nB\n"},
        })
        out = self.tmp / "out"
        proc = run_export("--repo-root", str(repo), "--profiles",
                          "alpha,beta", "--out", str(out))
        self.assertOneLineError(proc, "agents/foo.md")
        self.assertFalse(out.exists())

    def test_unknown_profile_exits_nonzero(self):
        out = self.tmp / "out"
        proc = run_export("--profiles", "cnc-machining,no-such-profile",
                          "--out", str(out))
        self.assertOneLineError(proc, "no-such-profile")
        self.assertFalse(out.exists())


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(0 if result.wasSuccessful() else 1)
