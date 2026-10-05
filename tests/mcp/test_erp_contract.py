#!/usr/bin/env python3
"""Tests for the ERP connector contract and the reference MockErpConnector.

Stdlib unittest only. Run:  python3 tests/mcp/test_erp_contract.py
Exits non-zero on any failure.

Layout
------
- ``ContractSurface``, ``WireFormat``: the contract module itself.
- ``ConformanceSuite``: a mixin that exercises ANY ``ErpConnector`` through
  its public API only (no mock internals). ``MockConformance`` runs it
  against ``MockErpConnector``.
- ``MockSpecific``, ``RowCaps``: assertions that need the mock's internals
  (in-memory stores, ``audit_log``, bulk synthetic data).

Run the conformance suite against your own connector
----------------------------------------------------
Your connector must serve the synthetic fixture ``FIXTURE_PATH``
(``infra/mcp-servers/erp-connector/mock-data/erp_mock.json``) on its read
path, e.g. loaded into a test database / view, and use the ``clock`` it is
given for token expiry and "last N days" queries::

    import sys, unittest
    sys.path.insert(0, "<repo>/tests/mcp")
    import test_erp_contract as erp  # import the module, not names from it,
                                     # so the mock's TestCases stay out of yours

    class MyConnectorConformance(erp.ConformanceSuite, unittest.TestCase):
        APPROVAL_SECRET = erp.SECRET

        def make_connector(self, clock):
            return MyConnector(approval_secret=self.APPROVAL_SECRET,
                               clock=clock, ...)  # seeded with erp.FIXTURE_PATH

    if __name__ == "__main__":
        unittest.main()
"""

import contextlib
import copy
import dataclasses
import hashlib
import inspect
import io
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

ERP_DIR = Path(__file__).resolve().parents[2] / "infra" / "mcp-servers" / "erp-connector"
FIXTURE_PATH = ERP_DIR / "mock-data" / "erp_mock.json"
sys.path.insert(0, str(ERP_DIR))

from contract import (  # noqa: E402
    REASON_APPROVAL_ALREADY_USED,
    REASON_APPROVER_ROLE_NOT_PERMITTED,
    SENSITIVE_GROUPS,
    CallContext,
    CanonicalArgsError,
    ErpConnector,
    InventorySnapshot,
    ListResult,
    MachineRate,
    PurchasePrice,
    Tier,
    WriteResult,
    aware,
    canonical_args,
    clamp_max_rows,
    compute_action_hash,
    decimal_str,
    issue_approval_token,
    masked_field_names,
    to_jsonable,
    verify_approval_token,
)
from mock_connector import MockErpConnector  # noqa: E402

SECRET = b"unit-test-secret-not-real"
NOW = datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc)
FUTURE = datetime(2026, 5, 20, tzinfo=timezone.utc)
ITEMS = [{"part_no": "BR-12345", "qty": 10}]
APPROVER_ROLE = "plant-manager"  # in DEFAULT_APPROVER_ROLES for every write tool
WRITE_TOOLS = (
    "create_sales_order",
    "create_purchase_request",
    "update_inventory_movement",
    "close_sales_order",
)
AUDIT_KEYS = {
    "ts", "tool", "operator_id", "role", "channel", "request_id",
    "classification", "approver", "approver_role", "approval_id", "args_hash",
    "idempotency_key", "decision", "deny_reason",
}


def ctx(role="sales-coordinator", operator="u-requester", token=None, rid="req-1",
        tier=Tier.T1):
    return CallContext(
        operator_id=operator, role=role, channel="test:chan", request_id=rid,
        classification=tier, timestamp=NOW, approval_token=token,
    )


def make(data=None):
    return MockErpConnector(SECRET, data=data, clock=lambda: NOW)


def so_args(items=ITEMS):
    return {"customer_id": "C-A001", "items": items,
            "delivery_date": FUTURE, "po_reference": "PO-1"}


def token_for(tool, args, approver="u-approver", approver_role=APPROVER_ROLE, **kw):
    kw.setdefault("now", NOW)
    return issue_approval_token(SECRET, approver, compute_action_hash(tool, args),
                                approver_role=approver_role, **kw)


def approved_so(c, key="k-1", items=ITEMS):
    tok = token_for("create_sales_order", so_args(items))
    return c.create_sales_order(
        ctx(token=tok, rid="req-w"), "C-A001", items, FUTURE, "PO-1",
        idempotency_key=key)


# ─── The contract module ────────────────────────────────────


class ContractSurface(unittest.TestCase):
    def test_abstract_tools_take_callcontext(self):
        names = sorted(ErpConnector.__abstractmethods__)
        self.assertIn("create_sales_order", names)
        for name in names:
            if name == "verify_approval":  # token hook, not a tool
                continue
            sig = inspect.signature(getattr(ErpConnector, name))
            params = list(sig.parameters.values())
            self.assertGreaterEqual(len(params), 2, name)
            first = params[1]  # after self
            self.assertEqual(first.name, "ctx", name)
            hints = inspect.get_annotations(getattr(ErpConnector, name), eval_str=True)
            self.assertIs(hints["ctx"], CallContext, name)

    def test_no_free_string_operator_parameter(self):
        for name in ErpConnector.__abstractmethods__:
            sig = inspect.signature(getattr(ErpConnector, name))
            self.assertNotIn("operator", sig.parameters, name)

    def test_write_tools_have_required_kwonly_idempotency_key(self):
        for name in WRITE_TOOLS:
            p = inspect.signature(getattr(ErpConnector, name)).parameters["idempotency_key"]
            self.assertIs(p.kind, inspect.Parameter.KEYWORD_ONLY, name)
            self.assertIs(p.default, inspect.Parameter.empty, name)

    def test_list_tools_have_max_rows_and_fields(self):
        listers = [n for n in ErpConnector.__abstractmethods__ if n.startswith("list_")]
        self.assertTrue(listers)
        for name in listers:
            params = inspect.signature(getattr(ErpConnector, name)).parameters
            self.assertIn("max_rows", params, name)
            self.assertIn("fields", params, name)

    def test_verify_approval_is_abstract_and_contract_cannot_instantiate(self):
        self.assertIn("verify_approval", ErpConnector.__abstractmethods__)
        with self.assertRaises(TypeError):
            ErpConnector()

    def test_mock_implements_every_abstract_method(self):
        self.assertFalse(MockErpConnector.__abstractmethods__)

    def test_callcontext_validation(self):
        with self.assertRaises(ValueError):
            CallContext("", "r", "c", "id", Tier.T0, NOW)
        with self.assertRaises(ValueError):
            CallContext("u", "r", "c", "id", Tier.T0, datetime(2026, 1, 1))  # naive
        with self.assertRaises(ValueError):
            CallContext("u", "r", "c", "id", "T0", NOW)  # not a Tier
        c = ctx(token="secret-token")
        self.assertNotIn("secret-token", repr(c))
        self.assertNotIn("secret-token", json.dumps(c.audit_fields()))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            c.role = "x"

    def test_tiers(self):
        self.assertEqual([t.name for t in Tier], ["T0", "T1", "T2", "T3"])
        self.assertIs(Tier["T2"], Tier.T2)  # gateway string label -> Tier

    def test_python_floor_and_stdlib_only(self):
        for f in ("contract.py", "mock_connector.py"):
            text = (ERP_DIR / f).read_text(encoding="utf-8")
            for banned in ("import requests", "import pydantic", "import yaml"):
                self.assertNotIn(banned, text, f)

    def test_default_record_audit_writes_json_lines_to_stderr(self):
        class Plain(MockErpConnector):  # keeps the contract's default hook
            record_audit = ErpConnector.record_audit

        c = Plain(SECRET, clock=lambda: NOW)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            c.get_customer(ctx(token="tok-should-not-appear"), "C-A001")
            c.create_sales_order(ctx(token="tok-should-not-appear"), "C-A001", ITEMS,
                                 FUTURE, "PO-1", idempotency_key="k")
        lines = [json.loads(line) for line in buf.getvalue().splitlines()]
        self.assertEqual([e["tool"] for e in lines], ["get_customer", "create_sales_order"])
        self.assertEqual(lines[0]["request_id"], "req-1")
        self.assertEqual(lines[1]["decision"], "deny")
        self.assertNotIn("tok-should-not-appear", buf.getvalue())


class WireFormat(unittest.TestCase):
    def test_action_hash_is_stable_and_excludes_key(self):
        a = compute_action_hash("t", {"x": Decimal("1"), "y": [1, 2]})
        b = compute_action_hash("t", {"y": [1, 2], "x": Decimal("1")})
        self.assertEqual(a, b)
        self.assertNotEqual(a, compute_action_hash("t2", {"x": Decimal("1"), "y": [1, 2]}))

    def test_int_and_decimal_spellings_collapse_to_one_hash(self):
        hashes = {
            compute_action_hash("t", {"qty": q})
            for q in (10, Decimal("10"), Decimal("10.00"), Decimal("1E+1"))
        }
        self.assertEqual(len(hashes), 1)
        self.assertNotEqual(hashes.pop(), compute_action_hash("t", {"qty": Decimal("10.5")}))
        self.assertEqual(canonical_args({"q": Decimal("10.00")}), {"q": "10"})

    def test_decimal_str_edge_cases(self):
        cases = {
            Decimal("0.50"): "0.5", Decimal("-0"): "0", Decimal("0.000"): "0",
            Decimal("1E+3"): "1000", Decimal("-1.2300"): "-1.23", 7: "7",
            Decimal("123456789012345678901234567890.10"): "123456789012345678901234567890.1",
        }
        for value, want in cases.items():
            self.assertEqual(decimal_str(value), want, repr(value))
        for bad in (Decimal("NaN"), Decimal("Infinity"), Decimal("1E+999999999")):
            with self.assertRaises(CanonicalArgsError, msg=repr(bad)):
                decimal_str(bad)

    def test_float_is_rejected_with_a_clear_error(self):
        with self.assertRaises(CanonicalArgsError) as cm:
            compute_action_hash("t", {"items": [{"part_no": "X", "qty": 10.0}]})
        self.assertIn("float", str(cm.exception))
        self.assertIn("args.items[0].qty", str(cm.exception))
        self.assertTrue(issubclass(CanonicalArgsError, ValueError))

    def test_datetimes_are_utc_z_and_naive_is_rejected(self):
        tpe = datetime(2026, 5, 20, 8, 0, tzinfo=ZoneInfo("Asia/Taipei"))
        self.assertEqual(canonical_args({"d": tpe}), {"d": "2026-05-20T00:00:00Z"})
        self.assertEqual(compute_action_hash("t", {"d": tpe}),
                         compute_action_hash("t", {"d": FUTURE}))
        with self.assertRaises(CanonicalArgsError):
            compute_action_hash("t", {"d": datetime(2026, 5, 20)})
        with self.assertRaises(CanonicalArgsError):
            compute_action_hash("t", {1: "non-string key"})

    def test_golden_vector(self):
        # Pinned so the approval service (chat gateway) can reproduce it
        # byte for byte: same JSON text, same hash.
        args = {"customer_id": "C-A001",
                "items": ({"part_no": "BR-12345", "qty": Decimal("10.00")},),
                "delivery_date": datetime(2026, 5, 20, 8, 0, tzinfo=ZoneInfo("Asia/Taipei")),
                "po_reference": "PO-客戶-1"}
        text = ('{"args":{"customer_id":"C-A001","delivery_date":"2026-05-20T00:00:00Z",'
                '"items":[{"part_no":"BR-12345","qty":"10"}],"po_reference":"PO-客戶-1"},'
                '"tool":"create_sales_order"}')
        want = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.assertEqual(want, "sha256:89dd2d286dd6ab1c90eac72608f640379a5820295bde8ac1233ebc36c3be71a5")
        self.assertEqual(compute_action_hash("create_sales_order", args), want)

    def test_token_format_and_verification(self):
        h = compute_action_hash("create_sales_order", so_args())
        tok = issue_approval_token(SECRET, "u-approver", h, approver_role="sales-manager",
                                   now=NOW, approval_id="ap-1")
        parts = tok.split("|")
        self.assertEqual(parts[:4], ["v1", "u-approver", "sales-manager", "ap-1"])
        self.assertEqual(len(parts), 6)
        d = verify_approval_token(SECRET, tok, h, now=NOW)
        self.assertEqual((d.valid, d.approver_id, d.approver_role, d.approval_id),
                         (True, "u-approver", "sales-manager", "ap-1"))
        promoted = tok.replace("|sales-manager|", "|plant-manager|")
        self.assertEqual(verify_approval_token(SECRET, promoted, h, now=NOW).reason,
                         "approval_signature_invalid")
        self.assertEqual(verify_approval_token(SECRET, tok, h, now=NOW + timedelta(hours=1)).reason,
                         "approval_expired")
        with self.assertRaises(ValueError):
            issue_approval_token(SECRET, "a|b", h, approver_role="r")
        for junk in (None, 123, "v1|a|r|b|1|é", "v1|a|r|b|-1|x", "v1|a||b|1|x"):
            self.assertFalse(verify_approval_token(SECRET, junk, h, now=NOW).valid, repr(junk))

    def test_to_jsonable_round_trip(self):
        c = make()
        cu = c.get_customer(ctx("quote-specialist"), "C-A001")
        wr = approved_so(c)
        inv = c.list_inventory(ctx(), fields=["part_no", "on_hand", "last_movement_at"])
        out = json.loads(json.dumps(to_jsonable({"cu": cu, "wr": wr, "inv": inv}),
                                    ensure_ascii=False))
        self.assertEqual(Decimal(out["cu"]["credit_limit"]), cu.credit_limit)
        self.assertEqual(out["cu"]["credit_limit"], "5000000")
        self.assertIsNone(out["cu"]["contact_email"])
        self.assertEqual(out["cu"]["masked_fields"], list(cu.masked_fields))
        self.assertTrue(out["wr"]["timestamp"].endswith("Z"))
        self.assertEqual(datetime.fromisoformat(out["wr"]["timestamp"].replace("Z", "+00:00")),
                         wr.timestamp)
        self.assertEqual(out["wr"]["status"], "committed")
        row = next(r for r in out["inv"]["rows"] if r["part_no"] == "PL-30007")
        self.assertEqual(Decimal(row["on_hand"]), Decimal("900.5"))
        self.assertEqual(row["last_movement_at"], "2026-04-21T02:10:00Z")
        self.assertEqual(out["inv"]["total_matched"], 3)  # ints stay numbers
        with self.assertRaises(CanonicalArgsError):
            to_jsonable({"x": 1.5})

    def test_result_types_reject_naive_datetimes_and_aware_helper(self):
        naive = datetime(2026, 1, 1, 8, 0)
        with self.assertRaises(ValueError):
            InventorySnapshot("p", Decimal(1), Decimal(1), Decimal(1), "A", naive)
        with self.assertRaises(ValueError):
            PurchasePrice("p", None, "TWD", naive)
        with self.assertRaises(ValueError):
            MachineRate("m", None, None, NOW, valid_to=naive)
        MachineRate("m", None, None, NOW)  # valid_to optional
        local = aware(naive, "Asia/Taipei")
        self.assertEqual(local.astimezone(timezone.utc), datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc))
        self.assertIs(aware(NOW, "Asia/Taipei"), NOW)  # already aware: unchanged
        snap = InventorySnapshot("p", Decimal(1), Decimal(1), Decimal(1), "A", local)
        self.assertIsNotNone(snap.last_movement_at.tzinfo)
        fields = dict(ok=True, status="committed", tool="t", idempotency_key="k",
                      action_hash="sha256:0", operator_id="u", role="r", channel="c",
                      request_id="i", classification="T1")
        with self.assertRaises(ValueError):
            WriteResult(**fields, timestamp=naive)

    def test_list_result_total_matched_optional_and_has_more(self):
        r = ListResult(rows=[{"a": 1}], total_matched=None, max_rows_applied=1,
                       truncated=True, fields=("a",))
        self.assertTrue(r.has_more)
        self.assertIsNone(r.total_matched)
        with self.assertRaises(ValueError):
            ListResult(rows=[], total_matched=-1, max_rows_applied=1, truncated=False, fields=())

    def test_custom_sensitive_group(self):
        groups = {**SENSITIVE_GROUPS, "special_quote": frozenset({"special_price"})}
        grants = {"quote-specialist": {"price"}, "sales-coordinator": {"price", "special_quote"}}
        self.assertIn("special_price", masked_field_names("quote-specialist", grants, groups))
        self.assertNotIn("special_price", masked_field_names("sales-coordinator", grants, groups))
        self.assertNotIn("special_price", masked_field_names("quote-specialist", grants))


# ─── Conformance suite (any ErpConnector) ───────────────────


class ConformanceSuite:
    """Contract tests that use only the public ``ErpConnector`` API.

    Mix into a ``unittest.TestCase`` and implement ``make_connector(clock)``.
    Optional hooks let a subclass add backend-specific checks
    (``written_count``, ``assert_written``); token minting can be replaced
    via ``issue_token`` if your approval service is not the canonical HMAC
    token. Audit events are captured by wrapping ``record_audit`` on the
    instance, so connectors need no ``audit_log`` attribute.
    """

    APPROVAL_SECRET = SECRET

    # --- hooks -------------------------------------------------------------

    def make_connector(self, clock):
        """Return a fresh connector serving FIXTURE_PATH and using ``clock``."""
        raise NotImplementedError

    def issue_token(self, tool, args, *, approver="u-approver",
                    approver_role=APPROVER_ROLE, ttl_seconds=900, secret=None):
        return issue_approval_token(
            secret or self.APPROVAL_SECRET, approver, compute_action_hash(tool, args),
            approver_role=approver_role, ttl_seconds=ttl_seconds, now=NOW)

    def written_count(self, tool):
        """Records your backend holds for ``tool``; None = not observable."""
        return None

    def assert_written(self, tool, record_id):
        """Assert ``record_id`` exists in your backend (optional)."""

    # --- plumbing ----------------------------------------------------------

    def setUp(self):
        self.c = self.connect()

    def connect(self, clock=None):
        c = self.make_connector(clock or (lambda: NOW))
        events = []
        original = c.record_audit

        def capture(event):
            events.append(event)
            original(event)

        c.record_audit = capture
        self.audit_events = events
        return c

    def approved_so(self, key="k-1", items=ITEMS):
        tok = self.issue_token("create_sales_order", so_args(items))
        return self.c.create_sales_order(
            ctx(token=tok, rid="req-w"), "C-A001", items, FUTURE, "PO-1",
            idempotency_key=key)

    def assertWrittenCount(self, tool, n):
        got = self.written_count(tool)
        if got is not None:
            self.assertEqual(got, n, tool)

    def assertRefused(self, res, reason):
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "refused")
        self.assertEqual(res.reason, reason)
        self.assertIsNone(res.record_id)
        self.assertWrittenCount("create_sales_order", 0)

    # --- masking -----------------------------------------------------------

    def test_quote_specialist_sees_price_not_contact(self):
        cu = self.c.get_customer(ctx("quote-specialist"), "C-A001")
        self.assertEqual(cu.credit_limit, Decimal("5000000"))
        self.assertIsNone(cu.contact_email)
        self.assertIsNone(cu.contact_name)
        self.assertIn("contact_email", cu.masked_fields)
        part = self.c.get_part_master(ctx("quote-specialist"), "BR-12345")
        self.assertEqual(part.standard_cost, Decimal("182.50"))

    def test_sales_coordinator_sees_both(self):
        cu = self.c.get_customer(ctx("sales-coordinator"), "C-A001")
        self.assertEqual(cu.contact_email, "buyer-a@example.invalid")
        self.assertEqual(cu.masked_fields, ())

    def test_inventory_manager_and_unknown_role_see_neither(self):
        for role in ("inventory-manager", "operator", "some-new-role"):
            cu = self.c.get_customer(ctx(role), "C-A001")
            self.assertIsNone(cu.credit_limit, role)
            self.assertIsNone(cu.contact_phone, role)
            part = self.c.get_part_master(ctx(role), "BR-12345")
            self.assertIsNone(part.standard_cost, role)
            rate = self.c.get_machine_rate(ctx(role), "CNC#3")
            self.assertIsNone(rate.hourly_rate, role)
            self.assertIn("hourly_rate", rate.masked_fields)
            st = self.c.get_credit_status(ctx(role), "C-B002")
            self.assertIsNone(st.available, role)
            self.assertTrue(st.warnings)  # warnings are not masked
            pp = self.c.get_recent_purchase_price(ctx(role), "BR-12345")
            self.assertIsNotNone(pp)  # exists, but price hidden
            self.assertIsNone(pp.unit_price, role)
            self.assertEqual(pp.masked_fields, ("unit_price",))

    def test_unmasked_price_for_granted_role(self):
        pp = self.c.get_recent_purchase_price(ctx("quote-specialist"), "BR-12345")
        self.assertEqual(pp.unit_price, Decimal("151.00"))
        self.assertIsNone(self.c.get_recent_purchase_price(ctx("quote-specialist"), "PL-30007"))

    def test_list_masks_by_role_and_ignores_requested_masked_fields(self):
        res = self.c.list_customers(ctx("inventory-manager"))
        for row in res.rows:
            self.assertNotIn("credit_limit", row)
            self.assertNotIn("contact_email", row)
            self.assertIn("name", row)
        self.assertIn("contact_email", res.masked_fields)
        res = self.c.list_customers(
            ctx("inventory-manager"), fields=["id", "contact_email", "credit_limit"])
        self.assertEqual(set(res.rows[0]), {"id"})
        self.assertEqual(res.masked_fields, ("contact_email", "credit_limit"))
        res = self.c.list_customers(ctx("sales-coordinator"), fields=["id", "contact_email"])
        self.assertEqual(set(res.rows[0]), {"id", "contact_email"})

    def test_list_parts_masks_cost(self):
        rows = self.c.list_parts(ctx("operator")).rows
        self.assertTrue(rows and all("standard_cost" not in r for r in rows))
        rows = self.c.list_parts(ctx("quote-specialist")).rows
        self.assertTrue(all("standard_cost" in r for r in rows))

    def test_unknown_field_is_an_error(self):
        with self.assertRaises(ValueError):
            self.c.list_customers(ctx(), fields=["id", "no_such_field"])
        with self.assertRaises(ValueError):
            self.c.list_customers(ctx(), fields="id")  # bare string

    def test_role_grant_override_can_only_be_set_explicitly(self):
        c = self.connect()
        c.role_grants = {"operator": {"price"}}
        self.assertEqual(c.get_part_master(ctx("operator"), "BR-12345").standard_cost,
                         Decimal("182.50"))
        self.assertIsNone(c.get_part_master(ctx("sales-coordinator"), "BR-12345").standard_cost)

    def test_custom_sensitive_fields_are_masked(self):
        self.c.sensitive_groups = {**SENSITIVE_GROUPS, "spec_sheet": frozenset({"spec"})}
        res = self.c.list_parts(ctx("quote-specialist"), fields=["part_no", "spec"])
        self.assertEqual(set(res.rows[0]), {"part_no"})
        self.assertEqual(res.masked_fields, ("spec",))

    # --- row caps ----------------------------------------------------------

    def test_explicit_small_cap_and_no_truncation(self):
        c = self.c
        res = c.list_customers(ctx(), max_rows=2)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)
        res = c.list_customers(ctx())
        self.assertEqual(len(res.rows), 3)
        self.assertFalse(res.truncated)
        with self.assertRaises(ValueError):
            c.list_customers(ctx(), max_rows=0)

    def test_caps_reported_default_200_hard_1000(self):
        res = self.c.list_customers(ctx())
        self.assertEqual(res.max_rows_applied, 200)
        self.assertIn(res.total_matched, (None, 3))
        res = self.c.list_customers(ctx(), max_rows=50000)
        self.assertEqual(res.max_rows_applied, 1000)
        self.assertEqual(res.has_more, res.truncated)

    def test_filters_and_inventory_list(self):
        c = self.c
        self.assertEqual(len(c.list_customers(ctx(), grade="A").rows), 1)
        low = c.list_inventory(ctx(), below_safety_stock=True).rows
        self.assertEqual({r["part_no"] for r in low}, {"SH-20001"})

    # --- approval ----------------------------------------------------------

    def test_no_token(self):
        res = self.c.create_sales_order(ctx(), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "approval_required")

    def test_garbage_and_forged_token(self):
        for tok in ("garbage", "v1|a|b|9999999999|deadbeef", "v1|a|b|notint|x",
                    "v1|a|plant-manager|b|9999999999|deadbeef"):
            res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE,
                                            "PO-1", idempotency_key="k")
            self.assertFalse(res.ok, tok)
            self.assertIn(res.reason, ("approval_malformed", "approval_signature_invalid"))
        self.assertWrittenCount("create_sales_order", 0)

    def test_token_signed_with_wrong_secret(self):
        tok = self.issue_token("create_sales_order", so_args(), secret=b"other-secret")
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "approval_signature_invalid")

    def test_token_bound_to_arguments(self):
        tok = self.issue_token("create_sales_order", so_args())  # approved qty 10
        tampered = [{"part_no": "BR-12345", "qty": 10000}]
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", tampered, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "approval_signature_invalid")

    def test_token_bound_to_tool(self):
        tok = self.issue_token("create_purchase_request", {"items": ITEMS, "urgency": "normal"})
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertFalse(res.ok)

    def test_expired_token(self):
        tok = self.issue_token("create_sales_order", so_args(), ttl_seconds=60)
        c = self.connect(lambda: NOW + timedelta(seconds=61))
        res = c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                   idempotency_key="k")
        self.assertEqual(res.reason, "approval_expired")
        self.assertFalse(res.ok)

    def test_self_approval_refused(self):
        tok = self.issue_token("create_sales_order", so_args(), approver="u-requester")
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "self_approval")

    def test_role_not_permitted_even_with_valid_token(self):
        tok = self.issue_token("create_sales_order", so_args())
        res = self.c.create_sales_order(ctx(role="operator", token=tok), "C-A001", ITEMS,
                                        FUTURE, "PO-1", idempotency_key="k")
        self.assertRefused(res, "role_not_permitted")

    def test_approver_role_must_be_allowed_for_tool(self):
        tok = self.issue_token("create_sales_order", so_args(), approver_role="quote-specialist")
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, REASON_APPROVER_ROLE_NOT_PERMITTED)
        self.c.approver_roles = {"create_sales_order": {"quote-specialist"}}
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertEqual(res.status, "committed")
        self.assertEqual(res.approver_role, "quote-specialist")

    def test_valid_token_commits(self):
        res = self.approved_so()
        self.assertTrue(res.ok)
        self.assertEqual(res.status, "committed")
        self.assertEqual(res.approver_id, "u-approver")
        self.assertEqual(res.approver_role, APPROVER_ROLE)
        self.assertTrue(res.record_id)
        self.assert_written("create_sales_order", res.record_id)

    def test_all_write_tools_refuse_without_token(self):
        c = self.c
        k = "k-x"
        results = [
            c.create_sales_order(ctx(), "C-A001", ITEMS, FUTURE, "PO", idempotency_key=k),
            c.create_purchase_request(ctx("inventory-manager"), ITEMS, "normal", idempotency_key=k),
            c.update_inventory_movement(ctx("inventory-manager"), "BR-12345", Decimal("1"),
                                        "in", "WO-1", idempotency_key=k),
            c.close_sales_order(ctx(), "SO-MOCK-00001", {"doc": 1}, idempotency_key=k),
        ]
        for r in results:
            self.assertFalse(r.ok, r.tool)
            self.assertEqual(r.reason, "approval_required", r.tool)
        for tool in WRITE_TOOLS:
            self.assertWrittenCount(tool, 0)
        self.assertEqual(c.get_inventory(ctx(), "BR-12345").on_hand, Decimal("420"))

    def test_verify_approval_never_raises_on_junk(self):
        for tok in (None, "", "x", "v1|||", "v1|a|b|c|d|e", 123, "v1|a|r|b|1|é"):
            d = self.c.verify_approval(tok, "sha256:00")
            self.assertFalse(d.valid)

    def test_idempotency_key_validation(self):
        for bad in ("", "  ", "x" * 129, "a\nb"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.c.create_sales_order(ctx(), "C-A001", ITEMS, FUTURE, "PO-1",
                                          idempotency_key=bad)

    def test_one_approval_authorises_exactly_one_write(self):
        tok = self.issue_token("create_sales_order", so_args())

        def call(key):
            return self.c.create_sales_order(
                ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1", idempotency_key=key)

        first = call("k-1")
        self.assertEqual(first.status, "committed")
        for key in ("k-2", "k-3"):
            again = call(key)
            self.assertFalse(again.ok, key)
            self.assertEqual(again.reason, REASON_APPROVAL_ALREADY_USED, key)
            self.assertIsNone(again.record_id)
        retry = call("k-1")  # the same write, retried: still fine
        self.assertEqual((retry.status, retry.record_id), ("replayed", first.record_id))
        self.assertWrittenCount("create_sales_order", 1)

    # --- idempotency -------------------------------------------------------

    def test_same_key_same_result_no_duplicate(self):
        r1 = self.approved_so("k-1")
        r2 = self.approved_so("k-1")
        self.assertEqual(r1.status, "committed")
        self.assertEqual(r2.status, "replayed")
        self.assertTrue(r2.ok)
        self.assertEqual(r1.record_id, r2.record_id)
        self.assertWrittenCount("create_sales_order", 1)

    def test_different_key_creates_new_record(self):
        r1 = self.approved_so("k-1")  # each approved_so() is a fresh approval
        r2 = self.approved_so("k-2")
        self.assertNotEqual(r1.record_id, r2.record_id)
        self.assertWrittenCount("create_sales_order", 2)

    def test_same_key_different_arguments_is_conflict(self):
        self.approved_so("k-1")
        r = self.approved_so("k-1", items=[{"part_no": "BR-12345", "qty": 99}])
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "idempotency_key_conflict")
        self.assertWrittenCount("create_sales_order", 1)

    def test_inventory_movement_replay_same_record(self):
        args = {"part_no": "BR-12345", "qty": Decimal("5"), "direction": "out",
                "reference": "WO-1"}
        c = ctx("inventory-manager", token=self.issue_token("update_inventory_movement", args))
        r1 = self.c.update_inventory_movement(c, "BR-12345", Decimal("5"), "out", "WO-1",
                                              idempotency_key="mv-1")
        r2 = self.c.update_inventory_movement(c, "BR-12345", Decimal("5"), "out", "WO-1",
                                              idempotency_key="mv-1")
        self.assertEqual((r1.status, r2.status), ("committed", "replayed"))
        self.assertEqual(r1.record_id, r2.record_id)
        self.assertWrittenCount("update_inventory_movement", 1)

    def test_create_then_close_sales_order(self):
        so = self.approved_so("k-1").record_id
        args = {"so_id": so, "shipment_doc": {"doc": "S-1"}}
        c = ctx(token=self.issue_token("close_sales_order", args))
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-1")
        self.assertTrue(r.ok)
        self.assertEqual(r.record_id, so)
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-1")
        self.assertEqual(r.status, "replayed")
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-2")
        self.assertEqual(r.reason, REASON_APPROVAL_ALREADY_USED)

    def test_purchase_request(self):
        args = {"items": ITEMS, "urgency": "urgent"}
        c = ctx("inventory-manager", token=self.issue_token("create_purchase_request", args))
        r = self.c.create_purchase_request(c, ITEMS, "urgent", idempotency_key="pr-1")
        self.assertTrue(r.ok)
        self.assert_written("create_purchase_request", r.record_id)

    # --- audit -------------------------------------------------------------

    def test_write_result_audit_fields_committed_and_refused(self):
        ok = self.approved_so()
        refused = self.c.create_sales_order(ctx(rid="req-r"), "C-A001", ITEMS, FUTURE,
                                            "PO-1", idempotency_key="k-r")
        for res in (ok, refused):
            rec = res.audit_record()
            self.assertTrue(AUDIT_KEYS <= set(rec), AUDIT_KEYS - set(rec))
            self.assertEqual(rec["operator_id"], "u-requester")
            self.assertEqual(rec["role"], "sales-coordinator")
            self.assertEqual(rec["channel"], "test:chan")
            self.assertEqual(rec["classification"], "T1")
            self.assertTrue(rec["args_hash"].startswith("sha256:"))
            self.assertTrue(rec["idempotency_key"])
            self.assertTrue(rec["request_id"])
            self.assertIsNotNone(res.timestamp.tzinfo)
        self.assertEqual(ok.audit_record()["decision"], "allow")
        self.assertEqual(ok.audit_record()["approver"], "u-approver")
        self.assertEqual(ok.audit_record()["approver_role"], APPROVER_ROLE)
        self.assertEqual(refused.audit_record()["decision"], "deny")
        self.assertEqual(refused.audit_record()["deny_reason"], "approval_required")

    def test_every_call_is_audited_and_token_never_logged(self):
        tok = self.issue_token("create_sales_order", so_args())
        self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                  idempotency_key="k-1")
        self.c.get_customer(ctx("operator", rid="req-2"), "C-A001")
        self.c.list_parts(ctx("operator", rid="req-3"))
        self.c.get_customer(ctx(rid="req-4"), "NOPE")
        events = self.audit_events
        self.assertEqual(len(events), 4)
        self.assertNotIn(tok, json.dumps(events, default=str))
        self.assertTrue(all("request_id" in e and "operator_id" in e for e in events))
        self.assertEqual([e["request_id"] for e in events], ["req-1", "req-2", "req-3", "req-4"])
        self.assertEqual(events[0]["access"], "write")
        self.assertEqual(events[1]["access"], "read")


class MockConformance(ConformanceSuite, unittest.TestCase):
    def make_connector(self, clock):
        return MockErpConnector(SECRET, clock=clock)

    def written_count(self, tool):
        stores = {"create_sales_order": self.c.sales_orders,
                  "create_purchase_request": self.c.purchase_requests,
                  "update_inventory_movement": self.c.movements}
        return len(stores[tool]) if tool in stores else None

    def assert_written(self, tool, record_id):
        stores = {"create_sales_order": self.c.sales_orders,
                  "create_purchase_request": self.c.purchase_requests}
        if tool in stores:
            self.assertIn(record_id, stores[tool])


# ─── Mock-specific (needs MockErpConnector internals) ───────


class RowCaps(unittest.TestCase):
    def big(self, n):
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        base = data["customers"][0]
        data["customers"] = [
            {**copy.deepcopy(base), "id": f"C-{i:05d}"} for i in range(n)]
        return make(data)

    def test_clamp_helper(self):
        self.assertEqual(clamp_max_rows(None), 200)
        self.assertEqual(clamp_max_rows(5), 5)
        self.assertEqual(clamp_max_rows(1000), 1000)
        self.assertEqual(clamp_max_rows(10**9), 1000)
        for bad in (0, -1, True, "5", 2.5):
            with self.assertRaises(ValueError, msg=repr(bad)):
                clamp_max_rows(bad)

    def test_default_cap_200(self):
        res = self.big(1200).list_customers(ctx())
        self.assertEqual(len(res.rows), 200)
        self.assertEqual(res.max_rows_applied, 200)
        self.assertEqual(res.total_matched, 1200)
        self.assertTrue(res.truncated)

    def test_hard_cap_1000(self):
        res = self.big(1200).list_customers(ctx(), max_rows=50000)
        self.assertEqual(len(res.rows), 1000)
        self.assertEqual(res.max_rows_applied, 1000)
        self.assertTrue(res.truncated)


class MockSpecific(unittest.TestCase):
    def setUp(self):
        self.c = make()

    def test_inventory_movement_replay_applies_once(self):
        args = {"part_no": "BR-12345", "qty": Decimal("5"), "direction": "out",
                "reference": "WO-1"}
        tok = token_for("update_inventory_movement", args)
        c = ctx("inventory-manager", token=tok)
        r1 = self.c.update_inventory_movement(c, "BR-12345", Decimal("5"), "out", "WO-1",
                                              idempotency_key="mv-1")
        r2 = self.c.update_inventory_movement(c, "BR-12345", Decimal("5"), "out", "WO-1",
                                              idempotency_key="mv-1")
        self.assertEqual((r1.status, r2.status), ("committed", "replayed"))
        self.assertEqual(r1.record_id, r2.record_id)
        self.assertEqual(self.c.get_inventory(ctx(), "BR-12345").on_hand, Decimal("415"))
        self.assertEqual(len(self.c.movements), 1)

    def test_validation_refusal_is_not_cached(self):
        args = {"part_no": "BR-12345", "qty": Decimal("100000"), "direction": "out",
                "reference": "WO-1"}
        c = ctx("inventory-manager", token=token_for("update_inventory_movement", args))
        r = self.c.update_inventory_movement(c, "BR-12345", Decimal("100000"), "out",
                                             "WO-1", idempotency_key="mv-9")
        self.assertEqual(r.reason, "validation:insufficient_stock")
        self.assertEqual(self.c.movements, [])
        # A refused write does not consume the approval.
        self.assertEqual(self.c._approvals_used, {})

    def test_create_then_close_sales_order(self):
        so = approved_so(self.c, "k-1").record_id
        args = {"so_id": so, "shipment_doc": {"doc": "S-1"}}
        c = ctx(token=token_for("close_sales_order", args))
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-1")
        self.assertTrue(r.ok)
        self.assertEqual(self.c.sales_orders[so]["status"], "closed")
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-1")
        self.assertEqual(r.status, "replayed")
        fresh = ctx(token=token_for("close_sales_order", args))  # new approval
        r = self.c.close_sales_order(fresh, so, {"doc": "S-1"}, idempotency_key="close-2")
        self.assertEqual(r.reason, "validation:sales_order_not_open")

    def test_replayed_token_creates_one_order(self):
        # SCENARIO-SIM-R5 replay probe: 1 token x 3 keys used to make 3 orders.
        tok = token_for("create_sales_order", so_args())
        results = [
            self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                      idempotency_key=f"k-{i}")
            for i in range(3)
        ]
        self.assertEqual([r.status for r in results], ["committed", "refused", "refused"])
        self.assertEqual(len(self.c.sales_orders), 1)

    def test_every_call_is_audited_and_token_never_logged(self):
        c = self.c
        tok = token_for("create_sales_order", so_args())
        c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                             idempotency_key="k-1")
        c.get_customer(ctx("operator"), "C-A001")
        c.list_parts(ctx("operator"))
        c.get_customer(ctx(), "NOPE")
        self.assertEqual(len(c.audit_log), 4)
        self.assertNotIn(tok, json.dumps(c.audit_log, default=str))
        self.assertTrue(all("request_id" in e and "operator_id" in e for e in c.audit_log))
        self.assertEqual(c.audit_log[1]["access"], "read")
        self.assertIn("standard_cost", c.audit_log[2]["masked_fields"])

    def test_mock_data_is_synthetic_json(self):
        text = FIXTURE_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
        self.assertTrue(data["customers"])
        self.assertIn("example.invalid", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
