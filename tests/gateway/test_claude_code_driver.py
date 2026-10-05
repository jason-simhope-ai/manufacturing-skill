#!/usr/bin/env python3
"""Tests for the claude-code harness driver (WP5), using a FAKE `claude` executable.

The fake is a small Python script written to a temp dir; it records argv, cwd, env and stdin,
and prints canned JSON. No real `claude` binary and no network are used.

Usage:
    python3 tests/gateway/test_claude_code_driver.py
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GW_DIR = REPO_ROOT / "infra" / "chat-gateway"
sys.path.insert(0, str(GW_DIR))

from chat_gateway.drivers import load_driver_class  # noqa: E402
from chat_gateway.drivers.base import DriverError, TwinInvocation, TwinResult  # noqa: E402
from chat_gateway_ext.claude_code import (  # noqa: E402
    REQUIRED_FLAGS, TWIN_RESULT_SCHEMA, ClaudeCodeDriver)

# Built by concatenation so repo secret scanners never see a literal key.
SECRET = "sk" + "-ant-" + "FAKE-test-key-0123456789"
FULL_HELP = """Usage: claude [options] [command] [prompt]
Options:
  -p, --print                      Print response and exit
  --output-format <format>         Output format
  --restricted                     Restricted mode
  --strict-mcp-config              Only use MCP servers from --mcp-config
  --tools <tools...>               Available tools
  --system-prompt[-file] <prompt>  System prompt (or file)
  --json-schema <schema>           JSON Schema for structured output
  --no-session-persistence         Disable session persistence
  --max-budget-usd <amount>        Maximum dollar amount
  --allowed-tools <tools...>       Unrelated flag
"""

FAKE_SCRIPT = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys, time
    REC = {rec!r}
    def rd(name, default=""):
        try:
            return open(os.path.join(REC, name), encoding="utf-8").read()
        except OSError:
            return default
    argv = sys.argv[1:]
    if argv[:1] == ["--version"]:
        print("2.1.289 (Claude Code)")
        sys.exit(0)
    if argv[:1] == ["--help"]:
        print(rd("help.txt"))
        sys.exit(0)
    prompt_file = argv[argv.index("--system-prompt-file") + 1] if "--system-prompt-file" in argv else ""
    record = dict(argv=argv, cwd=os.getcwd(), env=dict(os.environ), stdin=sys.stdin.read(),
                  prompt_file=prompt_file, prompt_text=open(prompt_file, encoding="utf-8").read() if prompt_file else "",
                  prompt_mode=oct(os.stat(prompt_file).st_mode & 0o777) if prompt_file else "")
    with open(os.path.join(REC, "call.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh)
    mode = rd("mode", "ok").strip()
    if mode == "slow":
        time.sleep(30)
    if mode == "fail":
        sys.stderr.write("SECRET-STDERR-CONTENT")
        sys.exit(3)
    if mode == "badjson":
        print("this is not json")
        sys.exit(0)
    if mode == "iserror":
        print(json.dumps(dict(type="result", subtype="error_max_budget_usd", is_error=True)))
        sys.exit(0)
    body = rd("body.json", "")
    print(body)
''')

RESULT_OBJ = {
    "reply": "先確認批號，再看 NCR。", "citations": ["ref/skills/ncr-handling.md"], "assumed": ["批量 200 件"],
    "unverified": [], "confidence": "中", "decisionPoints": ["是否停線"], "proposedActions": [],
    "suggestTwin": None,
}
ENVELOPE = {"type": "result", "subtype": "success", "is_error": False, "result": "ignored",
            "structured_output": RESULT_OBJ, "total_cost_usd": 0.0123,
            "usage": {"input_tokens": 321, "output_tokens": 45}}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.rec = root / "rec"
        self.rec.mkdir()
        self.bin = root / "bin" / "claude"
        self.bin.parent.mkdir()
        self.bin.write_text(FAKE_SCRIPT.format(rec=str(self.rec)), encoding="utf-8")
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IXUSR)
        self.set_help(FULL_HELP)
        self.set_body(ENVELOPE)
        self.config_dir = root / "svc-config"
        self.config_dir.mkdir()
        self.state = root / "state"
        self.build = root / "repo" / "team" / ".build"
        (self.build / "twins").mkdir(parents=True)
        (self.build / "ref").mkdir()
        self.prompt = self.build / "twins" / "qa-manager.prompt.md"
        self.prompt.write_text("# 品保部主管分身\n核心規則。\n", encoding="utf-8")
        self.data = root / "data-t1"
        self.data.mkdir()
        self.env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(root / "home"),
                    "ANTHROPIC_API_KEY": SECRET, "AWS_SECRET_ACCESS_KEY": "leak-aws",
                    "SLACK_BOT_TOKEN": "leak-slack", "MFG_TEAM_AUDIT_HMAC_KEY": "leak-audit-key-0123456789",
                    "MFG_TEAM_STATE_DIR": str(self.state)}

    def set_help(self, text):
        (self.rec / "help.txt").write_text(text, encoding="utf-8")

    def set_body(self, obj):
        (self.rec / "body.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def set_mode(self, mode):
        (self.rec / "mode").write_text(mode, encoding="utf-8")

    def driver(self, **kw):
        args = dict(bin=str(self.bin), config_dir=str(self.config_dir), max_budget_usd=0.10, timeout_s=60,
                    data_root=None, state_dir=self.state, env=self.env)
        args.update(kw)
        return ClaudeCodeDriver(**args)

    def inv(self, **kw):
        args = dict(twin_id="qa-manager", prompt_path=str(self.prompt), user_text="NCR-001 怎麼處理？",
                    channel_window=({"role": "user", "text": "早安", "tainted": False},), tier="T1",
                    effective_autonomy="suggest", timeout_s=60, max_budget_usd=0.10)
        args.update(kw)
        return TwinInvocation(**args)

    def call(self) -> dict:
        return json.loads((self.rec / "call.json").read_text(encoding="utf-8"))


class TestSelfCheck(Base):
    def test_pass(self):
        self.assertEqual(self.driver().self_check(), [])

    def test_each_missing_flag_is_reported(self):
        for flag, spellings in REQUIRED_FLAGS:
            with self.subTest(flag=flag):
                text = FULL_HELP
                for sp in spellings:
                    text = text.replace(sp, "--removed-flag")
                if flag == "--print":
                    text = text.replace("-p,", "")
                self.set_help(text)
                problems = self.driver().self_check()
                self.assertTrue(any(flag in p for p in problems), problems)

    def test_plain_system_prompt_flag_is_not_enough(self):
        self.set_help(FULL_HELP.replace("--system-prompt[-file]", "--system-prompt"))
        self.assertTrue(any("--system-prompt-file" in p for p in self.driver().self_check()))

    def test_full_spelling_accepted(self):
        self.set_help(FULL_HELP.replace("--system-prompt[-file]", "--system-prompt-file"))
        self.assertEqual(self.driver().self_check(), [])

    def test_tools_flag_not_satisfied_by_allowed_tools(self):
        self.set_help(FULL_HELP.replace("  --tools <tools...>               Available tools\n", ""))
        self.assertTrue(any("--tools" in p for p in self.driver().self_check()))

    def test_config_dir_missing_or_file(self):
        self.assertTrue(any("CONFIG_DIR" in p for p in self.driver(config_dir=str(self.state / "nope")).self_check()))
        f = Path(self._tmp.name) / "afile"
        f.write_text("x")
        self.assertTrue(any("CONFIG_DIR" in p for p in self.driver(config_dir=str(f)).self_check()))

    def test_config_dir_must_not_be_home_claude(self):
        home = Path(self._tmp.name) / "home"
        (home / ".claude").mkdir(parents=True)
        self.env["HOME"] = str(home)
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        try:
            problems = self.driver(config_dir=str(home / ".claude")).self_check()
        finally:
            if old is None:
                del os.environ["HOME"]
            else:
                os.environ["HOME"] = old
        self.assertTrue(any("~/.claude" in p for p in problems), problems)

    def test_missing_key_reported_without_value(self):
        del self.env["ANTHROPIC_API_KEY"]
        problems = self.driver().self_check()
        self.assertTrue(any("ANTHROPIC_API_KEY" in p for p in problems))
        self.env["ANTHROPIC_API_KEY"] = SECRET
        self.assertEqual(self.driver().self_check(), [])

    def test_alias_key_var_accepted_and_forwarded(self):
        del self.env["ANTHROPIC_API_KEY"]
        self.env["MFG_TEAM_ANTHROPIC_API_KEY"] = "sk-alias-key"
        self.assertEqual(self.driver().self_check(), [])
        self.driver().run(self.inv())
        self.assertEqual(self.call()["env"]["ANTHROPIC_API_KEY"], "sk-alias-key")
        self.assertNotIn("MFG_TEAM_ANTHROPIC_API_KEY", self.call()["env"])

    def test_problems_never_contain_the_key(self):
        self.set_help("nothing useful")
        self.assertNotIn(SECRET, " ".join(self.driver(config_dir="/nonexistent").self_check()))

    def test_missing_binary(self):
        problems = self.driver(bin=str(self.bin) + "-missing").self_check()
        self.assertTrue(any("not found" in p for p in problems))

    def test_data_root_must_exist(self):
        self.assertTrue(any("DATA_T1" in p for p in self.driver(data_root=str(self.data / "x")).self_check()))
        self.assertEqual(self.driver(data_root=str(self.data)).self_check(), [])


class TestRun(Base):
    def test_returns_twin_result_with_usage(self):
        res = self.driver().run(self.inv())
        self.assertIsInstance(res, TwinResult)
        self.assertEqual(res.reply, RESULT_OBJ["reply"])
        self.assertEqual(res.confidence, "中")
        self.assertEqual(res.decision_points, ("是否停線",))
        self.assertEqual(res.usage, {"input_tokens": 321, "output_tokens": 45, "cost_usd": 0.0123})

    def test_result_string_fallback_with_code_fence(self):
        env = {"type": "result", "subtype": "success", "is_error": False,
               "result": "```json\n" + json.dumps(RESULT_OBJ, ensure_ascii=False) + "\n```"}
        self.set_body(env)
        self.assertEqual(self.driver().run(self.inv()).reply, RESULT_OBJ["reply"])

    def test_exact_argv(self):
        self.driver().run(self.inv())
        argv = self.call()["argv"]
        pf = self.call()["prompt_file"]
        self.assertEqual(argv, [
            "-p", "--output-format", "json", "--restricted", "--strict-mcp-config", "--tools", "Read,Grep,Glob",
            "--system-prompt-file", pf, "--json-schema", argv[argv.index("--json-schema") + 1],
            "--no-session-persistence", "--max-budget-usd", "0.1"])
        self.assertEqual(json.loads(argv[argv.index("--json-schema") + 1]), TWIN_RESULT_SCHEMA)

    def test_no_shell_metacharacters_from_chat_in_argv(self):
        self.driver().run(self.inv(user_text="$(rm -rf /) ; `id` --add-dir /etc"))
        c = self.call()
        self.assertNotIn("rm -rf", " ".join(c["argv"]))
        self.assertNotIn("/etc", c["argv"])
        self.assertIn("rm -rf", c["stdin"])           # chat text goes only through stdin

    def test_user_text_and_window_via_stdin(self):
        self.driver().run(self.inv())
        stdin = self.call()["stdin"]
        self.assertIn("NCR-001 怎麼處理？", stdin)
        self.assertIn("早安", stdin)

    def test_budget_flag_value_is_min_of_driver_and_invocation(self):
        self.driver(max_budget_usd=0.25).run(self.inv(max_budget_usd=0.5))
        self.assertEqual(self.call()["argv"][-1], "0.25")
        self.driver(max_budget_usd=0.25).run(self.inv(max_budget_usd=0.05))
        self.assertEqual(self.call()["argv"][-1], "0.05")

    def test_add_dir_only_when_configured_and_granted(self):
        self.driver().run(self.inv(read_roots=(str(self.data),)))
        self.assertNotIn("--add-dir", self.call()["argv"])
        self.driver(data_root=str(self.data)).run(self.inv(read_roots=()))
        self.assertNotIn("--add-dir", self.call()["argv"])
        self.driver(data_root=str(self.data)).run(self.inv(read_roots=(str(self.data),)))
        argv = self.call()["argv"]
        self.assertEqual(argv[argv.index("--add-dir") + 1], str(self.data))

    def test_env_is_an_allowlist(self):
        self.driver().run(self.inv())
        env = self.call()["env"]
        self.assertEqual(env["ANTHROPIC_API_KEY"], SECRET)
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], str(self.config_dir))
        self.assertEqual(env["PATH"], self.env["PATH"])
        self.assertEqual(env["HOME"], self.env["HOME"])
        for leak in ("AWS_SECRET_ACCESS_KEY", "SLACK_BOT_TOKEN", "MFG_TEAM_AUDIT_HMAC_KEY", "MFG_TEAM_STATE_DIR"):
            self.assertNotIn(leak, env)
        # python itself may add a few vars (LC_CTYPE, ...); nothing from our fake secrets may appear
        self.assertNotIn("leak", json.dumps(env))
        extra = set(env) - {"PATH", "HOME", "CLAUDE_CONFIG_DIR", "ANTHROPIC_API_KEY"}
        self.assertLessEqual(extra, {"LC_CTYPE", "PWD", "SHLVL", "_", "LANG", "LC_ALL"})

    def test_cwd_is_build_dir_so_ref_prefix_resolves(self):
        self.driver().run(self.inv())
        self.assertEqual(os.path.realpath(self.call()["cwd"]), os.path.realpath(self.build))
        self.assertTrue((Path(self.call()["cwd"]) / "ref").is_dir())

    def test_system_prompt_file_has_header_and_is_removed(self):
        self.driver().run(self.inv(tainted=True, effective_autonomy="observe", predict_first=True))
        c = self.call()
        pf = Path(c["prompt_file"])
        self.assertTrue(str(pf).startswith(str(self.state)))
        self.assertIn("品保部主管分身", c["prompt_text"])
        self.assertIn("tier=T1 effectiveAutonomy=observe tainted=yes predictFirst=yes", c["prompt_text"])
        self.assertEqual(c["prompt_mode"], "0o600")
        self.assertFalse(pf.exists())
        self.assertEqual(list((self.state / "driver-tmp").iterdir()), [])

    def test_temp_file_removed_on_failure_too(self):
        for mode in ("fail", "badjson"):
            self.set_mode(mode)
            with self.assertRaises(DriverError):
                self.driver().run(self.inv())
            self.assertEqual(list((self.state / "driver-tmp").iterdir()), [], mode)

    def test_timeout_raises_driver_error_and_kills(self):
        self.set_mode("slow")
        t0 = time.monotonic()
        with self.assertRaises(DriverError) as cm:
            self.driver(timeout_s=1).run(self.inv(timeout_s=60))
        self.assertLess(time.monotonic() - t0, 15)
        self.assertIn("timed out", str(cm.exception))
        self.assertEqual(list((self.state / "driver-tmp").iterdir()), [])

    def test_invocation_timeout_also_caps(self):
        self.set_mode("slow")
        with self.assertRaises(DriverError):
            self.driver(timeout_s=60).run(self.inv(timeout_s=1))

    def test_nonzero_exit_is_short_message_without_stderr(self):
        self.set_mode("fail")
        with self.assertRaises(DriverError) as cm:
            self.driver().run(self.inv())
        self.assertIn("status 3", str(cm.exception))
        self.assertNotIn("SECRET-STDERR-CONTENT", str(cm.exception))

    def test_bad_json_is_driver_error(self):
        self.set_mode("badjson")
        with self.assertRaises(DriverError):
            self.driver().run(self.inv())

    def test_other_malformed_outputs(self):
        for body in ({"type": "result", "subtype": "success", "result": "not json at all"},
                     {"type": "result", "subtype": "success", "result": 5},
                     {"type": "result", "subtype": "success", "structured_output": {"nope": 1}},
                     {"type": "result", "subtype": "success", "structured_output": ["x"]},
                     ["unexpected"], 7):
            with self.subTest(body=body):
                self.set_body(body)
                with self.assertRaises(DriverError):
                    self.driver().run(self.inv())

    def test_cli_reported_error_is_driver_error(self):
        self.set_mode("iserror")
        with self.assertRaises(DriverError) as cm:
            self.driver().run(self.inv())
        self.assertIn("error_max_budget_usd", str(cm.exception))

    def test_missing_prompt_or_ref_dir(self):
        with self.assertRaises(DriverError):
            self.driver().run(self.inv(prompt_path=""))
        with self.assertRaises(DriverError):
            self.driver().run(self.inv(prompt_path=str(self.build / "twins" / "nope.prompt.md")))
        (self.build / "ref").rmdir()
        with self.assertRaises(DriverError):
            self.driver().run(self.inv())

    def test_key_never_in_argv_or_errors(self):
        self.driver().run(self.inv())
        self.assertNotIn(SECRET, json.dumps(self.call()["argv"]))
        self.set_mode("fail")
        with self.assertRaises(DriverError) as cm:
            self.driver().run(self.inv())
        self.assertNotIn(SECRET, str(cm.exception))

    def test_unstartable_binary(self):
        with self.assertRaises(DriverError):
            self.driver(bin=str(self.bin) + "-missing").run(self.inv())


class TestWiring(unittest.TestCase):
    def test_load_driver_class(self):
        self.assertIs(load_driver_class("claude-code"), ClaudeCodeDriver)
        self.assertEqual(ClaudeCodeDriver.name, "claude-code")

    def test_core_import_stays_clean_until_driver_loaded(self):
        """Importing every chat_gateway.* module must not pull in chat_gateway_ext, subprocess, asyncio or SaaS SDKs."""
        import subprocess as sp
        code = (
            "import sys, pkgutil, importlib, chat_gateway\n"
            "for m in pkgutil.walk_packages(chat_gateway.__path__, 'chat_gateway.'):\n"
            "    importlib.import_module(m.name)\n"
            "bad = [n for n in ('chat_gateway_ext', 'subprocess', 'asyncio', 'slack_sdk', 'discord') if n in sys.modules]\n"
            "print('BAD:' + ','.join(bad) if bad else 'CLEAN')\n"
            "from chat_gateway.drivers import load_driver_class\n"
            "from chat_gateway.adapters import load_adapter_class\n"
            "load_driver_class('mock'); load_adapter_class('mock')\n"
            "assert 'chat_gateway_ext' not in sys.modules\n"
            "load_driver_class('claude-code')\n"
            "assert 'chat_gateway_ext.claude_code' in sys.modules\n"
        )
        out = sp.run([sys.executable, "-c", code], cwd=GW_DIR, capture_output=True, text=True,
                     env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(GW_DIR)})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip().splitlines()[0], "CLEAN")

    def test_schema_file_matches_constant(self):
        path = GW_DIR / "chat_gateway_ext" / "twin_result.schema.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), TWIN_RESULT_SCHEMA)

    def test_schema_keys_match_result_contract(self):
        from chat_gateway.drivers.base import RESULT_KEYS
        self.assertEqual(set(TWIN_RESULT_SCHEMA["properties"]), set(RESULT_KEYS))

    def test_cli_constructor_signature(self):
        drv = ClaudeCodeDriver(bin="claude", config_dir="/x", max_budget_usd=0.1, timeout_s=60, data_root=None)
        self.assertEqual((drv.bin, drv.timeout_s, drv.data_root), ("claude", 60, None))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
