#!/usr/bin/env python3
"""Pilot-readiness tests (SCENARIO-SIM-R6 backlog S01, S03, S05, S08, S12 and review R-02).

Offline, stdlib unittest only, same fixtures as test_gateway.py.

Usage:
    python3 tests/gateway/test_pilot.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_gateway import (FIXTURES, GW_DIR, KEY, REPO_ROOT, Harness, HarnessCase,  # noqa: E402
                          chan, run_cli)

from chat_gateway import ConfigRefused, sanitize  # noqa: E402
from chat_gateway.adapters.base import ApprovalClick, ScheduledPost  # noqa: E402
from chat_gateway.audit import AuditLog, check_anchor, heads_document, verify_report  # noqa: E402
from chat_gateway.config import FREEZE_FILE, STATE_ENTRIES, config_from_env  # noqa: E402
from chat_gateway.core import DATA_ROOT_REPLY, FROZEN_REPLY, T3_REPLY  # noqa: E402
from chat_gateway.drivers.base import DriverPolicyDenied  # noqa: E402
from chat_gateway.drivers.mock import MockDriver  # noqa: E402

STARTER = REPO_ROOT / "team" / "tools" / "denylist.starter.txt"
TEAMCTL = REPO_ROOT / "team" / "tools" / "teamctl.py"

# SCENARIO-SIM-R6 §4: seven T2/T3 sentences that passed the built-in word list, with the tier the
# starter list must give them. One word is built by concatenation (generic T3 wording rule).
SEVEN = [
    ("P1", "客戶的航空發動機渦輪支架圖面 REV C，公差 ±0.005，這批要重新報價給對方採購", "T3"),
    ("P2", "The defense program fixture drawing DWG-4471 needs an export license before we send it "
           "to the subcontractor", "T3"),
    ("P3", "這個案子是客戶的專利設計，簽了保密協議，圖面不可外流，單價每件 85 元，客戶代號 K-17", "T2"),
    ("P4", "NDA project: missile guidance housing, tolerance 0.002 mm, Inconel 718, customer code K-17 "
           "wants 8D by Friday", "T3"),
    ("P5", "骨科植入物 Ti6Al4V 加工 NCR-0412，毛利 32%，客戶要求不得告知第三方", "T3"),
    ("P6", "這批要符合" + "軍" + "用規格 MIL-STD-810 振動測試，報告編號 TR-2026-044，客戶是政府標案", "T3"),
    ("P7", "這張單報價 125 萬、成本 98 萬，要不要接", "T2"),
]
CONTROL = "新台幣一百二十五萬，NTD 1,250,000"
# Everyday shop-floor wording the starter list must not block (false-positive set).
EVERYDAY = ["這批走航空件寄出", "航空公司改班機，稽核延到週四", "萬用表校正到期", "產量 3 萬件",
            "共 12 元件要換", "the agenda for Friday", "FUNDAMENTAL check", "defenseless", "implantation",
            "今天 NCR-0412 的 8D 進度", "SPC 管制圖異常", "Cpk 1.33 合格", "第 2 站 30 件"]


def tmpdir(case: unittest.TestCase, prefix: str) -> Path:
    d = Path(tempfile.mkdtemp(prefix=prefix))
    case.addCleanup(shutil.rmtree, d, True)
    return d


# ── S01: starter denylist and the T3: prefix ─────────────────────────
class TestStarterDenylist(HarnessCase):
    def setUp(self):
        self.extra = sanitize.load_denylist(STARTER)

    def test_seven_sentences_pass_without_and_are_caught_with_the_starter_list(self):
        for pid, text, want in SEVEN:
            with self.subTest(pid=pid):
                self.assertIsNone(sanitize.dlp_tier(text), "the built-in list alone is expected to miss this")
                self.assertEqual(sanitize.dlp_tier(text, self.extra), want)
        self.assertIsNone(sanitize.dlp_tier(CONTROL))
        self.assertEqual(sanitize.dlp_tier(CONTROL, self.extra), "T2")

    def test_everyday_wording_is_not_blocked(self):
        for text in EVERYDAY:
            with self.subTest(text=text):
                self.assertEqual(sanitize.dlp_hits(text, self.extra), [])

    def test_end_to_end_in_a_t1_channel(self):
        plain = self.make()
        for _pid, text, _want in SEVEN:
            plain.clock.t += 11                                  # stay under 6 messages per minute
            plain.msg("@品保 " + text)
        self.assertEqual(len(plain.driver.calls), 7)          # honest baseline: all seven reach the model
        h = self.make(extra_dlp=self.extra)
        for pid, text, want in SEVEN:
            with self.subTest(pid=pid):
                h.clock.t += 11
                [r] = h.msg("@品保 " + text)
                self.assertIn(f"dlp:{want}", h.reasons())
                if want == "T3":
                    self.assertIn(T3_REPLY, r.text)
        self.assertEqual(h.driver.calls, [])

    def test_t3_prefix_sets_the_tier_and_plain_lines_stay_t2(self):
        d = tmpdir(self, "deny-")
        path = d / "names.denylist"
        path.write_text("# comment\nT3:PRJ-X\\d{2}\nCUST-Z\\d{2}\n  T3:  (?i)secret-program  \n", encoding="utf-8")
        extra = sanitize.load_denylist(path)
        self.assertEqual([n for n, _ in extra], ["denylist-t3:2", "denylist:3", "denylist-t3:4"])
        self.assertEqual(sanitize.dlp_tier("見 PRJ-X12", extra), "T3")
        self.assertEqual(sanitize.dlp_tier("見 CUST-Z07", extra), "T2")
        self.assertEqual(sanitize.dlp_tier("the SECRET-Program kickoff", extra), "T3")
        _, stats = sanitize.filter_output("回覆提到 PRJ-X12", "T1", extra)
        self.assertEqual(stats["blocked"], "T3")
        path.write_text("T3:\n", encoding="utf-8")
        with self.assertRaises(ValueError) as cm:
            sanitize.load_denylist(path)
        self.assertIn("line 1", str(cm.exception))

    def test_deid_and_build_gateway_accept_the_prefix(self):
        sys.path.insert(0, str(REPO_ROOT / "team" / "tools"))
        import deid  # noqa: PLC0415
        pats = deid._load_denylist(STARTER)
        self.assertEqual(len(pats), len(self.extra))
        self.assertTrue(any(p.search("missile housing") for p in pats))
        from chat_gateway.__main__ import build_gateway  # noqa: PLC0415
        state = tmpdir(self, "state-") / "s"
        env = {"MFG_TEAM_STATE_DIR": str(state), "MFG_TEAM_DENYLIST": str(STARTER)}
        cfg = config_from_env(env, roster=str(FIXTURES / "roster.json"))
        with contextlib.redirect_stderr(io.StringIO()):
            gw = build_gateway(cfg, env)
        self.assertEqual(len(gw.extra_dlp), len(self.extra))

    def test_starter_file_holds_no_names_and_documents_itself(self):
        text = STARTER.read_text(encoding="utf-8")
        self.assertIn("T3:", text)
        self.assertIn("team/local/names.denylist", text)
        from chat_gateway.patterns import NAME_PATTERNS, find_secrets  # noqa: PLC0415
        self.assertEqual(find_secrets(text), [])
        for name, pat in NAME_PATTERNS:
            self.assertIsNone(pat.search(text), name)


# ── S03: kill switch ──────────────────────────────────────────────────
class TestFreeze(HarnessCase):
    def frozen_harness(self):
        flag = tmpdir(self, "flag-") / FREEZE_FILE
        h = self.make(frozen_flag=flag)
        return h, flag

    def test_flag_checked_before_every_event(self):
        h, flag = self.frozen_harness()
        [r] = h.msg("@品保 spc-watch")
        self.assertNotIn(FROZEN_REPLY, r.text)
        self.assertEqual(len(h.driver.calls), 1)
        flag.write_text("{}", encoding="utf-8")
        self.assertTrue(h.gw.frozen())
        [r] = h.msg("@品保 spc-watch")
        self.assertIn(FROZEN_REPLY, r.text)
        self.assertEqual(len(h.driver.calls), 1)                     # the model is not called
        self.assertEqual(h.records[-2]["action"], "frozen")
        self.assertEqual(h.records[-2]["deny_reason"], "frozen")
        self.assertEqual(h.records[-2]["channel"], "qa-floor")
        self.assertEqual(h.msg("@品保 again"), [])                    # one notice per user per minute
        h.clock.t += 61
        self.assertEqual(len(h.msg("@品保 again")), 1)
        self.assertEqual(h.msg("no mention", mentions_bot=False), [])
        self.assertEqual(h.msg("@品保 x", author_is_bot=True), [])
        self.assertEqual(h.msg("@品保 x", channel="nowhere"), [])
        self.assertEqual(h.gw.handle(ScheduledPost("production-manager", "briefing-risk-check", "daily-ops")), [])
        self.assertEqual(h.gw.handle(ApprovalClick("c1", "mock", "apv-00000000", "0" * 32, "mock-qa-lead",
                                                   "approve", h.clock(), "qa-floor")), [])
        self.assertEqual(h.actions().count("frozen"), 8)
        self.assertEqual(len(h.driver.calls), 1)
        flag.unlink()
        [r] = h.msg("@品保 spc-watch")
        self.assertNotIn(FROZEN_REPLY, r.text)
        self.assertEqual(len(h.driver.calls), 2)

    def test_freeze_wins_over_count_only_and_twin_free_day(self):
        # Merge of #15 (front-line count-only turns) and #38 (kill switch): frozen is checked first,
        # so 「我不同意」 and a twin-free-day ask are answered 「分身暫停服務中」 and counted as `frozen` only.
        def free_today(r):
            r["policy"]["timezone"] = "Asia/Taipei"
            chan(r, "qa-floor")["twinFreeDays"] = [5]
        flag = tmpdir(self, "flag-") / FREEZE_FILE
        flag.write_text("{}", encoding="utf-8")
        h = self.make(frozen_flag=flag, mutate=free_today)
        [r] = h.msg("@品保 我不同意")
        self.assertIn(FROZEN_REPLY, r.text)
        h.clock.t += 61
        [r] = h.msg("@品保 NCR-EX-012 嚴重度？")
        self.assertIn(FROZEN_REPLY, r.text)
        self.assertEqual(h.gw.handle(ScheduledPost("qa-manager", "spc-watch", "qa-floor")), [])
        acts = h.actions()
        for count_only in ("human_override", "practice_checkin", "twin_free_day"):
            self.assertNotIn(count_only, acts)
        self.assertEqual(acts.count("frozen"), 3)
        self.assertEqual(h.driver.calls, [])

    def test_unreadable_flag_counts_as_frozen(self):
        h, flag = self.frozen_harness()
        with mock.patch.object(Path, "lstat", side_effect=PermissionError):
            self.assertTrue(h.gw.frozen())

    def test_cli_freeze_unfreeze_and_run(self):
        tmp = tmpdir(self, "gw-freeze-")
        env = {"MFG_TEAM_STATE_DIR": str(tmp / "state")}
        p = run_cli(["-m", "chat_gateway", "freeze"], env)
        self.assertEqual(p.returncode, 0, p.stderr)
        flag = tmp / "state" / FREEZE_FILE
        self.assertTrue(flag.is_file())
        self.assertEqual(flag.stat().st_mode & 0o777, 0o600)
        self.assertEqual((tmp / "state").stat().st_mode & 0o777, 0o700)
        p = run_cli(["-m", "chat_gateway", "self-check", "--roster", str(FIXTURES / "roster.json")], env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("(frozen)", p.stdout)
        self.assertIn("FROZEN", p.stderr)
        script = tmp / "s.jsonl"
        script.write_text(json.dumps({"type": "message", "id": "x1", "channel": "qa-floor", "user": "mock-qa-lead",
                                      "text": "@品保 spc-watch"}, ensure_ascii=False) + "\n", encoding="utf-8")
        p = run_cli(["-m", "chat_gateway", "run", "--roster", str(FIXTURES / "roster.json"), "--script", str(script)],
                    env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(FROZEN_REPLY, p.stdout)
        self.assertNotIn("【品保部主管分身】", p.stdout)
        p = run_cli(["-m", "chat_gateway", "unfreeze"], env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(flag.exists())
        p = run_cli(["-m", "chat_gateway", "run", "--roster", str(FIXTURES / "roster.json"), "--script", str(script)],
                    env)
        self.assertIn("【品保部主管分身】", p.stdout)
        p = run_cli(["-m", "chat_gateway", "audit-verify", str(tmp / "state" / "audit")], env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(FREEZE_FILE, STATE_ENTRIES)                     # state-reset may move a frozen dir aside

    def test_freeze_refuses_a_symlinked_state_dir(self):
        tmp = tmpdir(self, "gw-freeze-")
        (tmp / "real").mkdir(mode=0o700)
        (tmp / "link").symlink_to(tmp / "real")
        p = run_cli(["-m", "chat_gateway", "freeze"], {"MFG_TEAM_STATE_DIR": str(tmp / "link")})
        self.assertEqual(p.returncode, 78, p.stderr)
        self.assertFalse((tmp / "real" / FREEZE_FILE).exists())


# ── S05: symlinked state dir refused before resolve() ────────────────
class TestStateDirSymlink(unittest.TestCase):
    def test_symlinked_state_dir_exits_78(self):
        tmp = tmpdir(self, "gw-link-")
        (tmp / "real").mkdir(mode=0o700)
        (tmp / "link").symlink_to(tmp / "real")
        with self.assertRaises(ConfigRefused) as cm:
            config_from_env({"MFG_TEAM_STATE_DIR": str(tmp / "link")})
        self.assertEqual(cm.exception.exit, 78)
        self.assertIn("symlink", str(cm.exception))
        p = run_cli(["-m", "chat_gateway", "self-check", "--roster", str(FIXTURES / "roster.json")],
                    {"MFG_TEAM_STATE_DIR": str(tmp / "link")})
        self.assertEqual(p.returncode, 78, p.stdout + p.stderr)
        self.assertIn("is a symlink", p.stderr)
        self.assertEqual(list((tmp / "real").iterdir()), [])          # nothing written through the link
        p = run_cli(["-m", "chat_gateway", "self-check", "--roster", str(FIXTURES / "roster.json")],
                    {"MFG_TEAM_STATE_DIR": str(tmp / "real")})
        self.assertEqual(p.returncode, 0, p.stderr)


# ── R-02: the ValueError branch prints the class name only ───────────
class TestErrorText(unittest.TestCase):
    def test_value_error_text_is_not_printed_but_usage_errors_are(self):
        import chat_gateway.__main__ as cli  # noqa: PLC0415
        env = {"MFG_TEAM_STATE_DIR": str(tmpdir(self, "gw-err-") / "s")}
        for exc in (ValueError("https://hooks.example.test/SECRET-URL"), ImportError("SECRET-MODULE-PATH"),
                    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "SECRET-BYTES")):
            with self.subTest(exc=type(exc).__name__):
                err = io.StringIO()
                with mock.patch.object(cli, "build_gateway", side_effect=exc), contextlib.redirect_stderr(err):
                    rc = cli.main(["self-check"], env=env)
                self.assertEqual(rc, 64)
                self.assertIn(f"chat_gateway: {type(exc).__name__}", err.getvalue())
                self.assertNotIn("SECRET", err.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = cli.main(["self-check", "--roster", str(FIXTURES / "roster.json")],
                          env={**env, "MFG_TEAM_ADAPTER": "bogus", "MFG_TEAM_AUDIT_HMAC_KEY": "k" * 16,
                               "MFG_TEAM_APPROVAL_HMAC_KEY": "a" * 16})
        self.assertEqual(rc, 64)
        self.assertIn("unknown adapter 'bogus'", err.getvalue())


# ── S08: off-host anchors ─────────────────────────────────────────────
class TestAuditAnchor(unittest.TestCase):
    def setUp(self):
        self.tmp = tmpdir(self, "gw-anchor-")
        self.root = self.tmp / "audit"
        self.log = AuditLog(self.root, KEY)
        for i in range(3):
            self.log.append(action="msg_in", channel_tier="T1", event_id=f"a{i}")
        self.log.append(action="config_loaded")

    def append(self, n: int, log=None):
        for i in range(n):
            (log or self.log).append(action="msg_in", channel_tier="T1", event_id=f"b{i}")

    def teamctl(self, *args):
        import subprocess  # noqa: PLC0415
        env = {"PATH": os.environ.get("PATH", ""), "MFG_TEAM_AUDIT_HMAC_KEY": KEY.decode()}
        return subprocess.run([sys.executable, str(TEAMCTL), "audit-verify", *map(str, args)],
                              capture_output=True, text=True, env=env, timeout=60)

    def test_rollback_of_log_and_checkpoint_together_is_caught_with_an_anchor(self):
        snapshot = self.tmp / "snapshot"
        shutil.copytree(self.root, snapshot)                         # what an attacker keeps
        self.append(3)
        anchor = self.tmp / "heads-week2.json"
        p = self.teamctl(self.root, "--heads-out", anchor)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("heads written", p.stdout)
        doc = json.loads(anchor.read_text(encoding="utf-8"))
        self.assertEqual((doc["kind"], doc["seq"], doc["tiers"]["T1"]["count"]), ("mfg-team-audit-heads", 7, 6))
        self.assertNotIn("msg_in", anchor.read_text(encoding="utf-8"))   # heads only, no records
        shutil.rmtree(self.root)
        shutil.copytree(snapshot, self.root)                         # roll back log AND checkpoint
        p = self.teamctl(self.root)
        self.assertEqual(p.returncode, 0, p.stdout)                  # without an anchor: undetectable
        self.assertIn("audit verify: OK (4)", p.stdout)
        p = self.teamctl(self.root, "--anchor", anchor)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("FAILED", p.stdout)
        self.assertIn("went down", p.stdout)

    def test_forward_progress_passes_and_a_rewritten_chain_fails(self):
        doc = heads_document(self.root, KEY)
        self.append(2)
        self.assertEqual(check_anchor(self.root, KEY, doc), [])
        # a key holder rebuilds T1 with different records but the same count: the anchored head is gone
        other = self.tmp / "other"
        log2 = AuditLog(other, KEY)
        for i in range(5):
            log2.append(action="msg_in", channel_tier="T1", event_id=f"forged{i}")
        log2.append(action="config_loaded")
        problems = check_anchor(other, KEY, doc)
        self.assertTrue(any("not on the current chain" in p for p in problems), problems)
        self.assertTrue(verify_report(other, KEY)[0])                # a plain verify cannot tell

    def test_anchor_tampering_and_wrong_key_are_refused(self):
        doc = heads_document(self.root, KEY)
        edited = json.loads(json.dumps(doc))
        edited["tiers"]["T1"]["count"] = 1
        self.assertIn("signature invalid", " ".join(check_anchor(self.root, KEY, edited)))
        self.assertIn("signature invalid", " ".join(check_anchor(self.root, b"another-key-0123456789", doc)))
        self.assertIn("not an audit heads document", " ".join(check_anchor(self.root, KEY, {"tiers": {}})))
        bad = self.tmp / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        p = self.teamctl(self.root, "--anchor", bad)
        self.assertEqual(p.returncode, 1)
        self.assertIn("unreadable", p.stdout)
        p = self.teamctl(self.root, "--anchor", self.tmp / "missing.json")
        self.assertEqual(p.returncode, 2)

    def test_tier_removed_or_truncated_since_the_anchor(self):
        self.append(2)
        doc = heads_document(self.root, KEY)
        doc_t1 = doc["tiers"]["T1"]
        fresh = self.tmp / "fresh"
        log = AuditLog(fresh, KEY)
        log.append(action="config_loaded")
        problems = check_anchor(fresh, KEY, doc)
        self.assertTrue(any("missing from the log now" in p for p in problems), problems)
        self.assertTrue(any("global seq went down" in p for p in problems), problems)
        self.assertEqual(doc_t1["count"], 5)

    def test_chat_gateway_cli_has_the_same_flags(self):
        anchor = self.tmp / "h.json"
        env = {"MFG_TEAM_AUDIT_HMAC_KEY": KEY.decode()}
        p = run_cli(["-m", "chat_gateway", "audit-verify", str(self.root), "--heads-out", str(anchor)], env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        p = run_cli(["-m", "chat_gateway", "audit-verify", str(self.root), "--anchor", str(anchor)], env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("anchor: OK", p.stdout)


# ── S12 / S10: driver info in config_loaded, policy_denied from a driver ──
class DescribingDriver(MockDriver):
    def describe(self):
        return {"cli_version": "2.1.289 (Claude Code)", "flag_check": "ok"}


class RefusingDriver(MockDriver):
    def run(self, inv):
        raise DriverPolicyDenied("data_root:T3")


class TestDriverReports(HarnessCase):
    def test_config_loaded_records_driver_info(self):
        h = self.make()
        self.assertEqual(h.records[0]["action"], "config_loaded")
        self.assertIsNone(h.records[0]["driver_info"])               # the mock driver reports nothing
        h2 = Harness()
        self.addCleanup(h2.close)
        h2.records.clear()
        from chat_gateway.core import Gateway  # noqa: PLC0415
        Gateway(h2.roster, h2.adapter, DescribingDriver(), h2.audit, h2.clock)
        self.assertEqual(h2.records[-1]["action"], "config_loaded")
        self.assertEqual(h2.records[-1]["driver_info"], {"cli_version": "2.1.289 (Claude Code)", "flag_check": "ok"})
        self.assertTrue(verify_report(h2.tmp / "state" / "audit", KEY)[0])

    def test_driver_policy_refusal_is_audited_as_policy_denied(self):
        h = self.make()
        h.gw.driver = RefusingDriver()
        [r] = h.msg("@品保 spc-watch")
        self.assertIn(DATA_ROOT_REPLY, r.text)
        rec = next(x for x in h.records if x["action"] == "policy_denied")
        self.assertEqual(rec["deny_reason"], "data_root:T3")
        self.assertEqual(rec["twin"], "qa-manager")
        self.assertNotIn("driver_error", h.actions())
        self.assertEqual(h.gw._failures.get("qa-manager", 0), 0)    # a policy refusal is not a failure


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
