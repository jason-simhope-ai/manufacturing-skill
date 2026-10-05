#!/usr/bin/env python3
"""Front-line controls in the gateway (SCENARIO-SIM-R7 E05, E06, E07, E10, E11, E13, E08):

* the reply reads as a reference, not an order (zh-TW header, fixed reference line);
* 「我不同意」/「分身錯了」 and 「我親手做了」 are count-only, audited without any user reference;
* twin-free days answer 「今天請自己判斷」 unless the message says 緊急;
* learners may @ the twin, get learner mode (≤ suggest, no verdict), default 我先說, and their
  turns never enter the channel window;
* audit-verify output never breaks counts down per person; demo --plain has no audit/token lines.

    python3 tests/gateway/test_frontline.py
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_gateway import GW_DIR, KEY, Harness, HarnessCase, chan, run_cli  # noqa: E402

from chat_gateway import ConfigRefused  # noqa: E402
from chat_gateway.__main__ import print_verify  # noqa: E402
from chat_gateway.adapters.base import ScheduledPost  # noqa: E402
from chat_gateway.audit import counts  # noqa: E402
from chat_gateway.core import (CHECKIN_REPLY, OVERRIDE_REPLY, TWIN_FREE_REPLY,  # noqa: E402
                               effective_autonomy)
from chat_gateway.drivers.base import TwinResult  # noqa: E402
from chat_gateway.formatter import LEARNER_LABEL, REFERENCE_LINE, VIEW_PREFIX, format_reply  # noqa: E402

USER_FIELDS = ("operator", "operator_ref", "event_id", "thread")


def learner_channel(r: dict) -> None:
    c = chan(r, "qa-floor")
    c["learners"] = ["qa-engineer"]
    c["predictFirstDefault"] = True


def free_on_the_5th(r: dict) -> None:
    r["policy"]["timezone"] = "Asia/Taipei"      # T0 is 2026-10-05 07:50 +08:00 (still the 4th in UTC)
    chan(r, "qa-floor")["twinFreeDays"] = [5]


class TestReplyWording(unittest.TestCase):
    def test_suggest_reads_as_a_reference(self):
        text = format_reply("品保部主管分身", "suggest", TwinResult(reply="看法", confidence="中"),
                            category="strengthen", seq=3)
        lines = text.splitlines()
        self.assertEqual(lines[0], "【品保部主管分身】· 建議（草稿）")
        self.assertEqual(lines[1], VIEW_PREFIX + "看法")
        self.assertEqual(lines[-2], REFERENCE_LINE)
        self.assertTrue(lines[-1].startswith("信心：中"))        # compact views keep the meta line last
        self.assertNotIn("結論：", text)
        self.assertNotIn("· suggest", text)

    def test_learner_label(self):
        text = format_reply("品保部主管分身", "suggest", TwinResult(reply="x"), category=None, seq=1, learner=True)
        self.assertTrue(text.startswith("【品保部主管分身】· " + LEARNER_LABEL))


class TestOverride(HarnessCase):
    def test_disagree_in_thread_is_counted_without_user_reference(self):
        h = self.make()
        [first] = h.msg("@品保 NCR-EX-012 我判中")
        calls = len(h.driver.calls)
        h.records.clear()
        [ack] = h.msg("@品保 我不同意，這件應該判高", thread_ref=first.thread_ref)
        self.assertEqual(len(h.driver.calls), calls)               # no new answer
        self.assertIn(OVERRIDE_REPLY, ack.text)
        self.assertEqual(ack.thread_ref, first.thread_ref)
        self.assertEqual([r["action"] for r in h.records], ["human_override", "msg_out"])
        rec = h.records[0]
        self.assertEqual((rec["channel"], rec["twin"], rec["capability"]), ("qa-floor", "qa-manager", "ncr-triage"))
        for r in h.records:
            for f in USER_FIELDS:
                self.assertIsNone(r[f], f)
        self.assertNotIn("msg_in", [r["action"] for r in h.records])

    def test_twin_was_wrong_and_unknown_thread(self):
        h = self.make()
        [ack] = h.msg("@品保 分身錯了 spc-watch 那則")
        self.assertIn(OVERRIDE_REPLY, ack.text)
        rec = h.records[-2]
        self.assertEqual((rec["action"], rec["capability"]), ("human_override", "spc-watch"))
        self.assertEqual(h.driver.calls, [])

    def test_anyone_identified_may_disagree_but_unknown_users_may_not(self):
        h = self.make()
        [ack] = h.msg("@品保 我不同意", user="mock-qa-eng")           # not an asker of qa-floor
        self.assertIn(OVERRIDE_REPLY, ack.text)
        self.assertEqual(h.msg("@品保 我不同意", user="stranger"), [])
        self.assertIn("unknown_identity", h.reasons())

    def test_overrides_are_rate_limited(self):
        h = self.make()
        for i in range(6):
            h.clock.t += 1
            self.assertTrue(h.msg(f"@品保 我不同意 {i}"))
        self.assertEqual(h.msg("@品保 我不同意 7"), [])
        self.assertEqual(sum(r["action"] == "human_override" for r in h.records), 6)
        self.assertEqual(h.records[-1]["action"], "rate_limited")
        self.assertIsNone(h.records[-1]["operator_ref"])

    def test_practice_checkin_is_count_only(self):
        h = self.make()
        [ack] = h.msg("@品保 我親手做了 ncr-triage 翻查")
        self.assertIn(CHECKIN_REPLY, ack.text)
        self.assertEqual(h.records[-2]["action"], "practice_checkin")
        self.assertIsNone(h.records[-2]["operator_ref"])
        self.assertEqual(h.driver.calls, [])

    def test_counts_and_verify_output_have_no_per_person_breakdown(self):
        h = self.make()
        h.msg("@品保 NCR-EX-012 我判中")                     # an ordinary turn: msg_in has an operator_ref
        h.msg("@品保 我不同意 ncr-triage")
        h.msg("@品保 我親手做了 ncr-triage")
        root = h.tmp / "state" / "audit"
        self.assertEqual(counts(root, KEY), {"human_override": {"qa-floor/ncr-triage": 1},
                                             "practice_checkin": {"qa-floor/ncr-triage": 1}})
        refs = {r["operator_ref"] for r in h.records if r["operator_ref"]}
        self.assertTrue(refs)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertTrue(print_verify(str(root), KEY))
        out = buf.getvalue()
        self.assertIn("human_override (count only, no per-person breakdown): qa-floor/ncr-triage=1", out)
        for ref in refs:
            self.assertNotIn(ref, out)
        self.assertNotIn("mock-qa-lead", out)
        self.assertNotIn("role:", out)


class TestTwinFreeDay(HarnessCase):
    def test_free_day_asks_people_to_judge_themselves(self):
        h = self.make(mutate=free_on_the_5th)
        [r] = h.msg("@品保 NCR-EX-012 嚴重度？")
        self.assertIn(TWIN_FREE_REPLY, r.text)
        self.assertEqual(h.driver.calls, [])
        rec = next(x for x in h.records if x["action"] == "twin_free_day")
        self.assertEqual((rec["channel"], rec["decision"]), ("qa-floor", "deny"))
        for f in USER_FIELDS:
            self.assertIsNone(rec[f], f)

    def test_urgent_and_other_channels_still_answer(self):
        h = self.make(mutate=free_on_the_5th)
        [r] = h.msg("@品保 緊急 NCR-EX-012 嚴重度？")
        self.assertIn(VIEW_PREFIX, r.text)
        [r] = h.msg("@生產 今日重點", user="mock-prod-lead", channel="daily-ops")
        self.assertIn(VIEW_PREFIX, r.text)
        self.assertEqual(len(h.driver.calls), 2)

    def test_scheduled_post_skipped_on_a_free_day(self):
        h = self.make(mutate=free_on_the_5th)
        self.assertEqual(h.gw.handle(ScheduledPost("qa-manager", "spc-watch", "qa-floor")), [])
        self.assertIn("twin_free_day", h.reasons())

    def test_day_boundary_uses_policy_timezone_else_utc(self):
        def utc_only(r):
            chan(r, "qa-floor")["twinFreeDays"] = [5]          # no policy.timezone: UTC, still the 4th
        h = self.make(mutate=utc_only)
        [r] = h.msg("@品保 NCR-EX-012 嚴重度？")
        self.assertIn(VIEW_PREFIX, r.text)

    def test_bad_days_and_bad_timezone_are_refused(self):
        with self.assertRaises(ConfigRefused):
            Harness(mutate=lambda r: chan(r, "qa-floor").__setitem__("twinFreeDays", [0]))

        def bad_tz(r):
            free_on_the_5th(r)
            r["policy"]["timezone"] = "Mars/Olympus"
        with self.assertRaises(ConfigRefused):
            Harness(mutate=bad_tz)


class TestLearner(HarnessCase):
    def test_learner_may_ask_and_gets_learner_mode(self):
        h = self.make(mutate=learner_channel)
        [r] = h.msg("@品保 NCR-EX-012 嚴重度怎麼判？", user="mock-qa-eng")
        inv = h.driver.calls[-1]
        self.assertTrue(inv.learner)
        self.assertTrue(inv.predict_first)                       # predictFirstDefault, ncr-triage eligible
        self.assertEqual(inv.effective_autonomy, "suggest")
        self.assertIn(LEARNER_LABEL, r.text.splitlines()[0])
        self.assertEqual(len(h.gw._window("qa-floor")), 0)        # the learner's draft never reaches others

    def test_skip_predict_first_once(self):
        h = self.make(mutate=learner_channel)
        h.msg("@品保 這次直接給 NCR-EX-012 相似案", user="mock-qa-eng")
        self.assertFalse(h.driver.calls[-1].predict_first)

    def test_askers_are_not_learners(self):
        h = self.make(mutate=learner_channel)
        h.msg("@品保 NCR-EX-012 嚴重度？")
        inv = h.driver.calls[-1]
        self.assertFalse(inv.learner)
        self.assertFalse(inv.predict_first)                      # default applies to learners only
        self.assertEqual(len(h.gw._window("qa-floor")), 2)

    def test_learner_never_above_suggest(self):
        cap = {"autonomy": "draft", "category": "strengthen"}
        twin = {"effectiveCeiling": "draft"}
        policy = {"autonomyCeiling": "draft"}
        channel = {"autonomyCeiling": "draft", "tier": "T1"}
        self.assertEqual(effective_autonomy(cap, twin, policy, channel), "draft")
        self.assertEqual(effective_autonomy(cap, twin, policy, channel, learner=True), "suggest")

    def test_learners_must_be_ids(self):
        with self.assertRaises(ConfigRefused):
            Harness(mutate=lambda r: chan(r, "qa-floor").__setitem__("learners", ["Not An Id"]))


class TestDemoPlain(unittest.TestCase):
    def test_plain_is_three_beats_without_audit_or_tokens(self):
        p = run_cli([str(GW_DIR / "demo.py"), "--plain"])
        self.assertEqual(p.returncode, 0, p.stderr)
        out = p.stdout
        self.assertEqual(out.count("━━ 第 "), 3)
        self.assertIn("第 3/3 段", out)
        for needle in ("audit", "tokens", "稽核 #", "US$", "(cron)", "【gateway】", "Beat "):
            self.assertNotIn(needle, out)
        self.assertIn(REFERENCE_LINE, out)

    def test_normal_mode_marks_beat_6_as_a_defence_test(self):
        p = run_cli([str(GW_DIR / "demo.py")])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("這是防線測試", p.stdout)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
