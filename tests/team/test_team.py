#!/usr/bin/env python3
"""Single entry point for the team-tier tests (WP1 data + WP2 tooling).

    python3 tests/team/test_team.py          # exits non-zero on any failure

Layers:
  * the YAML fixture runner (tests/team/run.py; also CI Step 19 on its own)
  * unit tests for the validator / compiler / deid internals
  * acceptance tests against the real repo (spec section 18 WP1 + WP2, 17.2/17.3)
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "team" / "tools"))
sys.path.insert(0, str(HERE))

import _teamlib as lib  # noqa: E402
import deid  # noqa: E402
import run as fixture_runner  # noqa: E402
import teamctl  # noqa: E402

TODAY = "2026-10-05"
EXAMPLE = REPO / "team" / "roster.example.yaml"
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def codes_of(findings, severity=None):
    return {f.code for f in findings
            if severity is None or f.severity == severity}


class FixtureRunner(unittest.TestCase):
    def test_all_fixture_cases_pass(self):
        total, failures = fixture_runner.run_all()
        self.assertEqual(failures, [], "\n" + "\n".join(failures))
        self.assertGreaterEqual(total, 20)

    def test_every_code_has_a_fixture_except_e051(self):
        data = fixture_runner.load_fixtures()
        covered = set()
        for case in data["cases"]:
            covered |= set(case["expect"].get("codes") or [])
        missing = sorted(set(lib.CODES) - covered - {"E051"})
        self.assertEqual(missing, [], "codes without a fixture case")

    def test_every_case_has_unique_id_and_expectation(self):
        data = fixture_runner.load_fixtures()
        ids = [c["id"] for c in data["cases"]] + [
            c["id"] for c in data["deid"]]
        self.assertEqual(len(ids), len(set(ids)))
        for c in data["cases"]:
            self.assertIn("exit", c["expect"], c["id"])


class RealExampleAcceptance(unittest.TestCase):
    """WP1 acceptance: teamctl check --ci exit 0; section 10.1 budgets hold."""

    def test_check_ci_exit_0(self):
        self.assertEqual(teamctl.main(["check", "--ci", "--today", TODAY]), 0)

    def test_no_findings_in_any_mode(self):
        for mode in ("ci", "local", "strict"):
            fs = lib.validate(REPO, EXAMPLE, mode=mode, today=TODAY)
            errors = [f.render() for f in fs if f.severity == "error"]
            self.assertEqual(errors, [], mode)

    def test_byte_budgets(self):
        sizes = {
            "TEAM.md": ((REPO / "TEAM.md").stat().st_size, 6000),
            "roster.example.yaml": (EXAMPLE.stat().st_size, 6144),
            "core-rules.md": (
                (REPO / "team/policies/core-rules.md").stat().st_size, 4096),
        }
        for p in (REPO / "team" / "twins").glob("*.md"):
            sizes[p.name] = (p.stat().st_size, 6144)
        for name, (n, limit) in sizes.items():
            self.assertLessEqual(n, limit, name)

    def test_build_budgets_and_cold_start(self):
        c = lib.compile_all(REPO, EXAMPLE)
        rj = c.files["roster.json"]
        self.assertLessEqual(len(rj), 4000)
        for t in json.loads(rj)["twins"]:
            self.assertLessEqual(len(lib.canon(t)), 600, t["id"])
        for name, data in c.files.items():
            if name.startswith("twins/"):
                self.assertLessEqual(len(data), 12000, name)
        summary = len(c.summary.encode("utf-8"))
        self.assertLessEqual(summary, 1200)
        cold = (REPO / "TEAM.md").stat().st_size + EXAMPLE.stat().st_size + (
            REPO / "team/policies/core-rules.md").stat().st_size + summary
        self.assertLessEqual(cold, 18432)

    def test_example_shape(self):
        r = lib.load_roster(EXAMPLE)
        self.assertIs(r["synthetic"], True)
        self.assertEqual(len(r["departments"]), 7)
        self.assertEqual(len(r["positions"]), 7)
        with_twin = {p["id"]: p["twin"] for p in r["positions"]
                     if "twin" in p}
        self.assertEqual(set(with_twin), {"production-manager", "qa-manager",
                                          "engineering-manager"})
        self.assertTrue(with_twin["qa-manager"]["enabled"])
        self.assertEqual(with_twin["qa-manager"]["needsTwinGate"]["result"],
                         "twin")
        self.assertFalse(with_twin["engineering-manager"]["enabled"])
        self.assertEqual(
            with_twin["engineering-manager"]["needsTwinGate"]["result"],
            "defer")
        self.assertEqual({p["incumbent"] for p in r["positions"]},
                         {"LOCAL", "VACANT"})
        self.assertEqual(len(r["channels"]), 3)
        for ch in r["channels"]:
            self.assertEqual((ch["tier"], ch["adapter"]), ("T1", "mock"))

    def test_pilot_twin_capabilities(self):
        def caps(tid):
            fm, _ = lib.load_twin(REPO / "team" / "twins" / f"{tid}.md")
            return {c["id"]: c for c in fm["capabilities"]}, fm

        pm, _ = caps("production-manager")
        self.assertEqual(pm["briefing-risk-check"]["category"], "strengthen")
        self.assertEqual(pm["delay-risk"]["category"], "create")
        self.assertEqual(pm["briefing-data-pack"]["category"], "outsource")
        self.assertIs(pm["briefing-data-pack"]["dormant"], True)
        qa, fm = caps("qa-manager")
        self.assertEqual({k: v["category"] for k, v in qa.items()}, {
            "ncr-triage": "strengthen", "8d-challenge": "strengthen",
            "spc-watch": "create", "8d-formatting": "outsource"})
        self.assertEqual(fm["compose"]["agent"], "quality-inspector")
        eng, fm = caps("engineering-manager")
        self.assertEqual(eng["ecn-impact-check"]["category"], "create")
        self.assertEqual(fm["compose"], {
            "agent": "engineering-change-manager",
            "skills": ["engineering-change-process", "bom-management"],
            "knowHow": ["eco-ecn"], "hooks": [], "optional": []})

    def test_build_is_deterministic_and_matches_contract(self):
        a = lib.compile_all(REPO, EXAMPLE)
        b = lib.compile_all(REPO, EXAMPLE)
        self.assertEqual(a.source_hash, b.source_hash)
        self.assertEqual(a.files, b.files)
        roster = json.loads(a.files["roster.json"])
        self.assertEqual(set(roster), {"builtBy", "channels", "org", "policy",
                                       "schema", "sourceHash", "twins"})
        self.assertEqual(a.files["roster.json"], lib.canon(roster))
        self.assertEqual([t["id"] for t in roster["twins"]],
                         ["production-manager", "qa-manager"])
        for t in roster["twins"]:
            self.assertEqual(set(t), {
                "aliases", "capabilities", "channels", "department",
                "effectiveCeiling", "id", "outsource", "prompt", "promptSha",
                "tierCeiling", "title", "vacant"})
            self.assertEqual(t["outsource"], {"dormant": 1, "enabled": 0})
            self.assertEqual(
                t["promptSha"], lib._sha(a.files[t["prompt"]]))
            self.assertTrue(all(c["category"] != "outsource"
                                for c in t["capabilities"]))
        for ch in roster["channels"]:
            self.assertEqual(set(ch), {
                "adapter", "askers", "autonomyCeiling", "defaultTwin",
                "department", "id", "tier", "twins"})

    def test_compiled_prompts(self):
        c = lib.compile_all(REPO, EXAMPLE)
        core = (REPO / "team/policies/core-rules.md").read_text(
            encoding="utf-8").rstrip("\n")
        roster = json.loads(c.files["roster.json"])
        channel_ids = [ch["id"] for ch in roster["channels"]]
        for t in roster["twins"]:
            text = c.files[t["prompt"]].decode("utf-8")
            self.assertTrue(text.startswith(core), "core-rules is not first")
            self.assertNotRegex(text, ISO_DATE)
            for cid in channel_ids:
                self.assertNotIn(cid, text)
            self.assertIn("TwinResult", text)
            self.assertNotIn("briefing-data-pack |", text)  # dormant hidden
            self.assertNotIn("8d-formatting |", text)
        self.assertEqual(c.findings, [])  # no W006 for the pilot twins

    def test_refs_are_copied_and_indexed(self):
        c = lib.compile_all(REPO, EXAMPLE)
        for rel in ("ref/skills/spc-basics.md", "ref/know-how/iso-9001.md",
                    "ref/hooks/on-error.md", "ref/agents/quality-inspector.md"):
            self.assertIn(rel, c.files)
        qa = c.files["twins/qa-manager.prompt.md"].decode("utf-8")
        # index lines are relative to team/.build/ref/ (the driver's cwd): no `ref/` prefix
        self.assertIn("\nskills/spc-basics.md — ", qa)
        self.assertNotIn("ref/skills/", qa)

    def test_engineering_twin_compiles_within_budget_when_enabled(self):
        """Wave 1b: enabling engineering-manager must still fit 12,000 B."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            import shutil
            for rel in ("core", "profiles", "team", "plugin.json", "TEAM.md",
                        ".gitignore"):
                src = REPO / rel
                if src.is_dir():
                    shutil.copytree(src, root / rel, ignore=shutil.ignore_patterns(
                        ".build", "local", "__pycache__"))
                else:
                    shutil.copy(src, root / rel)
            ro = root / "team" / "roster.example.yaml"
            ro.write_text(ro.read_text(encoding="utf-8").replace(
                "enabled: false\n      file: engineering-manager",
                "enabled: true\n      file: engineering-manager").replace(
                "result: defer", "result: twin"), encoding="utf-8")
            self.assertEqual(
                [f.render() for f in lib.validate(root, ro, mode="local",
                                                  today=TODAY)
                 if f.severity == "error"], [])
            c = lib.compile_all(root, ro)
            text = c.files["twins/engineering-manager.prompt.md"].decode()
            self.assertLessEqual(len(text.encode()), 12000)
            self.assertIn("ref/agents/engineering-change-manager.md",
                          "".join(c.files))
            self.assertNotIn("ref/agents/", text)   # cwd-relative index lines only

    def test_source_hash_changes_with_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            lib.build(REPO, EXAMPLE, out)
            h1 = json.loads((out / "roster.json").read_bytes())["sourceHash"]
        self.assertTrue(h1.startswith("sha256:"))
        self.assertEqual(len(h1), len("sha256:") + 64)
        base = fixture_runner.load_fixtures()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_runner.materialize(base["base"], {"id": "x"}, root)
            r = root / "team" / "roster.example.yaml"
            h_a = lib.compile_all(root, r).source_hash
            (root / "team/policies/core-rules.md").write_text("# changed\n")
            h_b = lib.compile_all(root, r).source_hash
        self.assertNotEqual(h_a, h_b)

    def test_cli_build_writes_expected_tree(self):
        import build
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(build.main(["--out", tmp, "--check-deterministic"]), 0)
            out = Path(tmp)
            self.assertTrue((out / "roster.json").is_file())
            self.assertTrue((out / "twins" / "qa-manager.prompt.md").is_file())
            self.assertFalse((out / "identities.json").exists())
            self.assertFalse((out / "bindings.json").exists())
            self.assertFalse((out / "twins" / "engineering-manager.prompt.md"
                              ).exists())


class OverlayBuild(unittest.TestCase):
    def test_identities_bindings_and_personal_overlay_compiled(self):
        base = fixture_runner.load_fixtures()
        case = {"id": "overlay-build", "files": {
            "team/local/identities.local.yaml":
                "users:\n  - {platform: mock, userId: demo, positions: [qa-manager]}\n",
            "team/local/bindings.local.yaml":
                "channels:\n  qa-floor: {platform: mock, ref: demo-channel}\n",
            "team/local/personal/qa-manager.local.md":
                "---\ntone: concise\naliases: [qa]\n---\nshort answers\n"},
            "copy": {"team/local/roster.local.yaml": "team/roster.example.yaml"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_runner.materialize(base["base"], case, root)
            res = lib.build(root, root / "team/local/roster.local.yaml",
                            root / "team" / ".build")
            self.assertIn("identities.json", res.files)
            self.assertIn("bindings.json", res.files)
            roster = json.loads(res.roster and lib.canon(res.roster))
            self.assertEqual(roster["twins"][0]["aliases"], ["qa"])
            prompt = (root / "team/.build/twins/qa-manager.prompt.md"
                      ).read_text(encoding="utf-8")
            self.assertIn("tone: concise", prompt)
            ident = json.loads((root / "team/.build/identities.json").read_text())
            self.assertEqual(ident["users"][0]["userId"], "demo")
            # the example roster never compiles overlays
            c = lib.compile_all(root, root / "team/roster.example.yaml")
            self.assertNotIn("identities.json", c.files)


class ProfileExtendsResolution(unittest.TestCase):
    def test_extends_profile_agent_is_resolved_not_copied(self):
        base = fixture_runner.load_fixtures()
        case = {"id": "extends-ref", "files": {
            "profiles/cnc-machining/agents/quality-inspector.md":
                "---\nname: quality-inspector\nextends: core/agents/quality-inspector"
                "\n---\n\n<!-- inherit -->\n\n## CNC 加碼\n\n加碼段落內容\n"}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture_runner.materialize(base["base"], case, root)
            ro = root / "team" / "roster.example.yaml"
            self.assertEqual([f for f in lib.validate(
                root, ro, mode="ci", today=TODAY) if f.severity == "error"], [])
            c = lib.compile_all(root, ro)
            ref = c.files["ref/agents/quality-inspector.md"].decode()
            self.assertIn("fixture body", ref)          # inherited core text
            self.assertIn("加碼段落內容", ref)             # profile addition
            self.assertNotIn("<!-- inherit -->", ref)
            self.assertNotIn("extends:", ref)
            prompt = c.files["twins/qa-manager.prompt.md"].decode()
            self.assertIn("加碼段落內容", prompt)         # embedded form is resolved
            self.assertNotIn("<!-- inherit -->", prompt)


class BudgetErrorsNeedingPatches(unittest.TestCase):
    """E050 variants a fixture cannot reach by file content alone."""

    def _with_budget(self, key, value):
        old = lib.BUDGETS[key]
        lib.BUDGETS[key] = value
        self.addCleanup(lib.BUDGETS.__setitem__, key, old)

    def test_e050_compiled_prompt_over_limit(self):
        self._with_budget("prompt", 2000)
        fs = lib.validate(REPO, EXAMPLE, mode="ci", today=TODAY)
        msgs = [f.message for f in fs if f.code == "E050"]
        self.assertTrue(any("compiled prompt" in m for m in msgs), msgs)

    def test_build_refuses_when_prompt_over_limit(self):
        self._with_budget("prompt", 2000)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(lib.BuildError):
                lib.build(REPO, EXAMPLE, tmp)

    def test_e050_cold_start_over_limit(self):
        self._with_budget("cold-start", 1000)
        fs = lib.validate(REPO, EXAMPLE, mode="ci", today=TODAY)
        self.assertTrue(any(f.code == "E050" and "cold start" in f.message
                            for f in fs))

    def test_e050_summary_over_limit(self):
        real = lib.render_summary
        lib.render_summary = lambda *a, **k: "x" * 1300  # truncation bypassed
        self.addCleanup(setattr, lib, "render_summary", real)
        fs = lib.validate(REPO, EXAMPLE, mode="ci", today=TODAY)
        self.assertTrue(any(f.code == "E050" and "summary" in f.message
                            for f in fs))

    def test_w006_when_agent_does_not_fit(self):
        self._with_budget("prompt", 6500)
        c = lib.compile_all(REPO, EXAMPLE)
        self.assertIn("W006", codes_of(c.findings))


class Determinism(unittest.TestCase):
    def test_e051_nondeterministic_build(self):
        real, counter = lib._render_prompt, [0]

        def noisy(*a, **k):
            counter[0] += 1
            text, findings = real(*a, **k)
            return text + f"<!-- run {counter[0]} -->\n", findings

        lib._render_prompt = noisy
        self.addCleanup(setattr, lib, "_render_prompt", real)
        fs = lib.validate(REPO, EXAMPLE, mode="ci", today=TODAY)
        self.assertIn("E051", codes_of(fs, "error"))
        self.assertTrue(lib.check_deterministic(REPO, EXAMPLE))


# Public names of team/tools/_teamlib.py before it became a shim over team/tools/teamlib/
# (snapshot taken at 6351d8b). The shim must keep exporting exactly these.
SHIM_PUBLIC_NAMES = (
    "ACTING_MAX_DAYS", "ADAPTERS", "ADAPTER_MAX_TIER", "AUTONOMY", "Any", "BUDGETS", "BUILT_BY",
    "BuildError", "BuildResult", "CATEGORY_LABEL", "CATEGORY_VALUES", "CODES", "Compiled", "Finding",
    "GATE_RESULTS", "GATE_STALE_DAYS", "IDENTITY_KEYS", "LoadError", "NAME_OTHER", "NAME_ZH",
    "OUTSOURCE_MAX_DAYS", "OUTSOURCE_WARN_DAYS", "PII_PATTERNS", "Path", "REF_PREFIX",
    "REQUIRED_GITIGNORE", "REQUIRED_SECTIONS", "SAFETY_KEYWORDS", "SECRET_PATTERNS", "TIERS",
    "TIER_CAP", "TOOL_REPO", "VERSION", "annotations", "build", "canon", "check_deterministic",
    "compile_all", "dataclasses", "default_roster", "dlp_scan", "effective_autonomy", "est_tokens",
    "find_ref", "fnmatch", "hashlib", "importlib", "json", "load_lint_allow", "load_roster",
    "load_twin", "re", "render_summary", "resolved_text", "shared_secret_patterns", "shutil",
    "split_frontmatter", "subprocess", "sys", "validate", "validate_ex", "yaml", "yaml_load",
)


class TeamlibShim(unittest.TestCase):
    def test_shim_exports_the_same_public_names(self):
        public = sorted(n for n in dir(lib) if not n.startswith("_"))
        self.assertEqual(public, sorted(SHIM_PUBLIC_NAMES))

    def test_shim_names_are_the_package_objects(self):
        import importlib
        pkg = importlib.import_module("teamlib")
        for name in pkg.__all__:
            self.assertIs(getattr(lib, name), getattr(pkg, name), name)
        for name in ("_render_prompt", "_Validator", "_date", "_sha", "_valid_date", "_tw_business_id_ok"):
            self.assertTrue(callable(getattr(lib, name)), name)

    def test_shim_assignment_reaches_the_defining_module(self):
        import importlib
        compile_mod = importlib.import_module("teamlib.compile")
        real = lib.render_summary
        lib.render_summary = sentinel = lambda *a, **k: "patched\n"
        try:
            self.assertIs(compile_mod.render_summary, sentinel)
        finally:
            lib.render_summary = real
        self.assertIs(compile_mod.render_summary, real)


class EffectiveAutonomy(unittest.TestCase):
    policy = {"autonomyCeiling": "draft"}
    twin = {"autonomyCeiling": "draft"}
    pos = {"incumbent": "LOCAL", "twin": {"autonomyCeiling": "draft"}}
    ch = {"autonomyCeiling": "draft", "tier": "T1"}

    def ea(self, cap, **kw):
        a = dict(twin=self.twin, position=self.pos, policy=self.policy,
                 channel=self.ch)
        a.update(kw)
        return lib.effective_autonomy(cap, **a)

    def test_minimum_of_all_layers(self):
        self.assertEqual(self.ea({"autonomy": "suggest"}), "suggest")
        self.assertEqual(self.ea({"autonomy": "act"}), "draft")
        self.assertEqual(self.ea({"autonomy": "draft"},
                                 channel={"autonomyCeiling": "observe",
                                          "tier": "T1"}), "observe")
        self.assertEqual(self.ea({"autonomy": "draft"},
                                 policy={"autonomyCeiling": "suggest"}),
                         "suggest")

    def test_outsource_never_above_draft(self):
        loose = {"autonomyCeiling": "act", "tier": "T1"}
        self.assertEqual(
            self.ea({"autonomy": "act", "category": "outsource"},
                    twin={"autonomyCeiling": "act"},
                    position={"twin": {"autonomyCeiling": "act"}},
                    policy={"autonomyCeiling": "act"}, channel=loose), "draft")

    def test_vacant_position_is_observe(self):
        pos = {"incumbent": "VACANT", "twin": {"autonomyCeiling": "draft"}}
        self.assertEqual(self.ea({"autonomy": "draft"}, position=pos),
                         "observe")

    def test_tier_caps(self):
        loose = {"autonomyCeiling": "act", "tier": "T2"}
        kw = dict(twin={"autonomyCeiling": "act"},
                  position={"twin": {"autonomyCeiling": "act"}},
                  policy={"autonomyCeiling": "act"})
        self.assertEqual(self.ea({"autonomy": "act"}, channel=loose, **kw),
                         "act-with-approval")
        loose["tier"] = "T3"
        self.assertEqual(self.ea({"autonomy": "act"}, channel=loose, **kw),
                         "draft")
        loose["tier"] = "T0"
        self.assertEqual(self.ea({"autonomy": "act"}, channel=loose, **kw),
                         "act")


class LoaderAndHelpers(unittest.TestCase):
    def test_dates_become_iso_strings_and_sexagesimal_stays_int(self):
        data = lib.yaml_load("d: 2026-10-05\nt: 2026-10-05 07:40:00\nx: 7:40\n")
        self.assertEqual(data["d"], "2026-10-05")
        self.assertIsInstance(data["t"], str)
        self.assertIsInstance(data["x"], int)  # -> E005 where a str is expected

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.yaml"
            p.write_text("a: 1\na: 2\n")
            with self.assertRaises(lib.LoadError):
                lib.load_roster(p)

    def test_token_estimate(self):
        self.assertEqual(lib.est_tokens("中文字" * 10), 30)
        self.assertEqual(lib.est_tokens("a" * 40), 10)

    def test_codes_table_is_complete(self):
        for code, text in lib.CODES.items():
            self.assertRegex(code, r"^[EW]\d{3}$")
            self.assertTrue(text.strip(), code)
        spec_errors = {"E001", "E002", "E003", "E004", "E005", "E010", "E011",
                       "E012", "E013", "E014", "E020", "E021", "E022", "E023",
                       "E024", "E030", "E031", "E032", "E033", "E034", "E035",
                       "E036", "E037", "E038", "E039", "E040", "E041", "E042",
                       "E043", "E044", "E045", "E046", "E047", "E050", "E051",
                       "E060"}
        self.assertEqual({c for c in lib.CODES if c[0] == "E"}, spec_errors)
        self.assertEqual({c for c in lib.CODES if c[0] == "W"},
                         {f"W00{i}" for i in range(1, 9)})

    def test_finding_render_is_ci_annotation(self):
        f = lib.Finding("E012", "error", "team/x.md", "line 3: x")
        self.assertEqual(f.render(), "::error file=team/x.md::E012: line 3: x")
        w = lib.Finding("W004", "warning", "a", "b")
        self.assertTrue(w.render().startswith("::warning file=a::W004:"))

    def test_business_id_checksum(self):
        self.assertTrue(lib._tw_business_id_ok("10000004"))
        self.assertFalse(lib._tw_business_id_ok("10000001"))


class DeidUnit(unittest.TestCase):
    def test_map_must_be_local_or_outside_repo(self):
        self.assertTrue(deid._map_is_safe(Path("deid-map.local.yaml")))
        self.assertTrue(deid._map_is_safe(Path("/somewhere/else/map.yaml")))
        self.assertFalse(deid._map_is_safe(REPO / "team" / "map.yaml"))

    def test_rows_core(self):
        header = ["customer", "desc"]
        rows = [["Alpha Co", "ok"], ["Beta Co", "Alpha Co again"]]
        mapping = {}
        h, out, counts, residual = deid.deid_rows(
            rows, header, mapping=mapping, customer_cols={"customer"},
            drop=set(), keep=set(), text_cols=set(), denylist=[])
        self.assertEqual(out, [["CUST-01", "ok"], ["CUST-02", "CUST-01 again"]])
        self.assertEqual(counts["customer"], 2)
        self.assertEqual(counts["customer_in_text"], 1)
        self.assertEqual(residual, [])
        self.assertEqual(mapping, {"Alpha Co": "CUST-01", "Beta Co": "CUST-02"})

    def test_outputs_are_private_and_names_fold(self):
        import stat
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "in.csv", Path(tmp) / "o.csv"
            mp = Path(tmp) / "deid-map.local.yaml"
            src.write_text("customer,desc\nＡＣＭＥ  Co,ok\n", encoding="utf-8")
            self.assertEqual(deid.main(["--in", str(src), "--out", str(out),
                                        "--map", str(mp)]), 0)
            for f in (out, mp):
                self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600, f)
            self.assertIn("ACME Co: CUST-01", mp.read_text(encoding="utf-8"))

    def test_unsafe_map_path_is_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.csv"
            src.write_text("customer\nFoo\n")
            rc = deid.main(["--in", str(src), "--out", str(Path(tmp) / "o.csv"),
                            "--map", str(REPO / "team" / "map.yaml")])
            self.assertEqual(rc, 2)
            self.assertFalse((REPO / "team" / "map.yaml").exists())


class DeidHonestReport(unittest.TestCase):
    def run_deid(self, csv_text, *extra, deny=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = Path(tmp.name)
        (d / "in.csv").write_text(csv_text, encoding="utf-8")
        if deny is not None:
            (d / "names.denylist").write_text(deny, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = deid.main(["--in", str(d / "in.csv"), "--out", str(d / "o.csv"),
                            "--map", str(d / "deid-map.local.yaml"), *extra])
        return rc, buf.getvalue(), d

    def test_clean_run_without_denylist_says_what_was_not_checked(self):
        rc, out, _ = self.run_deid("customer,desc\nAlpha Co,毛邊 DWG-AB12345\n")
        self.assertEqual(rc, 0)
        self.assertIn("residual hits=0", out)
        self.assertIn("WARNING no denylist loaded", out)
        self.assertIn("part-number scan = NOT scanned", out)
        self.assertIn("NOT scanned: English names", out)
        self.assertIn("at least 10 output rows", out)

    def test_denylist_entry_count_is_reported(self):
        rc, out, _ = self.run_deid("customer,desc\nAlpha Co,ok\n", deny="# c\nFOO-\\d+\nBAR\n")
        self.assertEqual(rc, 0)
        self.assertIn("denylist 2 entries", out)
        self.assertNotIn("no denylist loaded", out)

    def test_part_numbers_scanned_only_with_a_pattern(self):
        text = "customer,desc\nAlpha Co,孔徑偏大 DWG-AB12345\n"
        rc, _, _ = self.run_deid(text)
        self.assertEqual(rc, 0)                                   # no pattern: passes through
        rc, out, d = self.run_deid(text, "--partno-pattern", r"DWG-[A-Z]{2}\d{5}")
        self.assertEqual(rc, 1)
        self.assertIn("matches part-number", out)
        self.assertIn("regex 'DWG-[A-Z]{2}\\d{5}'", out)
        self.assertNotIn("DWG-AB12345", out)                      # values are never printed
        self.assertFalse((d / "o.csv").exists())
        rc, out, _ = self.run_deid(text, "--partno-pattern", "(")
        self.assertEqual(rc, 2)

    def test_ragged_rows_are_reported(self):
        rc, out, d = self.run_deid("customer,desc\nAlpha Co,hello,0912,extra\nBeta Co\n")
        self.assertEqual(rc, 0)
        self.assertIn("WARNING 2 row(s) do not have 2 cells (first: row 2 has 4)", out)


class CliExitCodes(unittest.TestCase):
    def test_audit_verify_missing_file_is_usage_error(self):
        self.assertEqual(teamctl.main(["audit-verify",
                                       "/nonexistent/audit.jsonl"]), 2)

    def test_audit_verify_real_chain_then_tamper(self):
        gw = REPO / "infra" / "chat-gateway"
        if not (gw / "chat_gateway" / "audit.py").is_file():
            self.skipTest("chat_gateway.audit not present")
        sys.path.insert(0, str(gw))
        try:
            from chat_gateway import audit
        except ImportError:
            self.skipTest("chat_gateway.audit not importable")
        with tempfile.TemporaryDirectory() as tmp:
            log = audit.AuditLog(tmp, b"k" * 32)
            log.append(action="msg_in", event_id="e1")
            log.append(action="msg_out", event_id="e1")
            from unittest import mock
            import io
            from contextlib import redirect_stderr, redirect_stdout
            with mock.patch.dict(os.environ, {"MFG_TEAM_AUDIT_HMAC_KEY": "k" * 32}), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(teamctl.main(["audit-verify", tmp]), 0)
            # without the key (demo key fallback) the keyed chain does not verify
            env = {k: v for k, v in os.environ.items() if k != "MFG_TEAM_AUDIT_HMAC_KEY"}
            with mock.patch.dict(os.environ, env, clear=True), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(teamctl.main(["audit-verify", tmp]), 1)
            f = next(Path(tmp).glob("*/audit.jsonl"))
            lines = f.read_text(encoding="utf-8").splitlines()
            with mock.patch.dict(os.environ, {"MFG_TEAM_AUDIT_HMAC_KEY": "k" * 32}), \
                    redirect_stdout(io.StringIO()) as buf:
                f.write_text(lines[0] + "\n", encoding="utf-8")       # tail truncated
                self.assertEqual(teamctl.main(["audit-verify", tmp]), 1)
                f.write_text("[]\n" + "\n".join(lines) + "\n", encoding="utf-8")
                self.assertEqual(teamctl.main(["audit-verify", str(f)]), 1)
            self.assertIn("not a JSON object", buf.getvalue())

    def test_state_reset_needs_confirm_and_only_moves_aside(self):
        from unittest import mock
        import io
        from contextlib import redirect_stderr, redirect_stdout
        base = Path(tempfile.mkdtemp(prefix="state-"))
        self.addCleanup(__import__("shutil").rmtree, base, True)
        state = base / "team"
        (state / "audit").mkdir(parents=True)
        (state / "audit" / "checkpoint.json").write_text("{}", encoding="utf-8")
        env = {**os.environ, "MFG_TEAM_STATE_DIR": str(state)}
        with mock.patch.dict(os.environ, env, clear=True):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(teamctl.main(["state-reset"]), 2)            # no --confirm: nothing moves
            self.assertTrue(state.is_dir())
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(teamctl.main(["state-reset", "--confirm"]), 0)
            moved = next(base.glob("team.stale-*"))
            self.assertFalse(state.exists())
            self.assertTrue((moved / "audit" / "checkpoint.json").is_file())  # kept, not deleted
            self.assertIn(str(moved), out.getvalue())
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(teamctl.main(["state-reset", "--confirm"]), 0)
            self.assertIn("nothing to move", out.getvalue())
            (state).mkdir()
            (state / "my-notes.txt").write_text("x", encoding="utf-8")        # not a gateway state dir
            with redirect_stderr(io.StringIO()) as err:
                self.assertEqual(teamctl.main(["state-reset", "--confirm"]), 2)
            self.assertIn("refusing", err.getvalue())
            self.assertTrue((state / "my-notes.txt").is_file())
        with mock.patch.dict(os.environ, {**env, "MFG_TEAM_STATE_DIR": "rel/dir"}, clear=True), \
                redirect_stderr(io.StringIO()):
            self.assertEqual(teamctl.main(["state-reset", "--confirm"]), 2)

    def test_dlp_scan_uses_the_ubn_cue_rule(self):
        self.assertEqual(lib.dlp_scan("交期 20230103"), [])
        self.assertEqual(lib.dlp_scan("工單 12345675"), [])
        self.assertEqual(lib.dlp_scan("統編 04595257"), ["tw-ubn"])

    def test_invalid_calendar_date_is_e005_not_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.yaml"
            p.write_text("schema: 1\nreviewedOn: 2026-02-30\n", encoding="utf-8")
            self.assertEqual(lib.load_roster(p)["reviewedOn"], "2026-02-30")
            self.assertFalse(lib._valid_date("2026-02-30"))

    def test_check_unknown_roster_is_io_error(self):
        self.assertEqual(teamctl.main(["check", "--roster", "/no/such.yaml"]), 2)

    def test_roster_json_subcommand(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = teamctl.main(["roster", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["org"],
                         "example-machinery-co")


if __name__ == "__main__":
    unittest.main(verbosity=1)
