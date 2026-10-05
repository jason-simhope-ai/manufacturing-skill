#!/usr/bin/env python3
"""Tests for the ERP connector contract and the reference MockErpConnector.

Stdlib unittest only. Run:  python3 tests/mcp/test_erp_contract.py
Exits non-zero on any failure.
"""

import copy
import dataclasses
import inspect
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ERP_DIR = Path(__file__).resolve().parents[2] / "infra" / "mcp-servers" / "erp-connector"
sys.path.insert(0, str(ERP_DIR))

from contract import (  # noqa: E402
    CallContext,
    ErpConnector,
    Tier,
    clamp_max_rows,
    compute_action_hash,
)
from mock_connector import MockErpConnector, issue_approval_token  # noqa: E402

SECRET = b"unit-test-secret-not-real"
NOW = datetime(2026, 4, 25, 9, 0, tzinfo=timezone.utc)
FUTURE = datetime(2026, 5, 20, tzinfo=timezone.utc)
ITEMS = [{"part_no": "BR-12345", "qty": 10}]
WRITE_TOOLS = (
    "create_sales_order",
    "create_purchase_request",
    "update_inventory_movement",
    "close_sales_order",
)
AUDIT_KEYS = {
    "ts", "tool", "operator_id", "role", "channel", "request_id",
    "classification", "approver", "args_hash", "idempotency_key",
    "decision", "deny_reason",
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
            "delivery_date": FUTURE.isoformat(), "po_reference": "PO-1"}


def token_for(tool, args, approver="u-approver", **kw):
    return issue_approval_token(SECRET, approver, compute_action_hash(tool, args),
                                now=NOW, **kw)


def approved_so(c, key="k-1", items=ITEMS):
    tok = token_for("create_sales_order", so_args(items))
    return c.create_sales_order(
        ctx(token=tok, rid="req-w"), "C-A001", items, FUTURE, "PO-1",
        idempotency_key=key)


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

    def test_python_floor_and_stdlib_only(self):
        for f in ("contract.py", "mock_connector.py"):
            text = (ERP_DIR / f).read_text(encoding="utf-8")
            for banned in ("import requests", "import pydantic", "import yaml"):
                self.assertNotIn(banned, text, f)


class Masking(unittest.TestCase):
    def setUp(self):
        self.c = make()

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
        c = make()
        c.role_grants = {"operator": {"price"}}
        self.assertEqual(c.get_part_master(ctx("operator"), "BR-12345").standard_cost,
                         Decimal("182.50"))
        self.assertIsNone(c.get_part_master(ctx("sales-coordinator"), "BR-12345").standard_cost)


class RowCaps(unittest.TestCase):
    def big(self, n):
        data = json.loads((ERP_DIR / "mock-data" / "erp_mock.json").read_text(encoding="utf-8"))
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

    def test_explicit_small_cap_and_no_truncation(self):
        c = make()
        res = c.list_customers(ctx(), max_rows=2)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)
        res = c.list_customers(ctx())
        self.assertEqual(len(res.rows), 3)
        self.assertFalse(res.truncated)
        with self.assertRaises(ValueError):
            c.list_customers(ctx(), max_rows=0)

    def test_filters_and_inventory_list(self):
        c = make()
        self.assertEqual(len(c.list_customers(ctx(), grade="A").rows), 1)
        low = c.list_inventory(ctx(), below_safety_stock=True).rows
        self.assertEqual({r["part_no"] for r in low}, {"SH-20001"})


class Approval(unittest.TestCase):
    def setUp(self):
        self.c = make()

    def assertRefused(self, res, reason):
        self.assertFalse(res.ok)
        self.assertEqual(res.status, "refused")
        self.assertEqual(res.reason, reason)
        self.assertIsNone(res.record_id)
        self.assertEqual(self.c.sales_orders, {})

    def test_no_token(self):
        res = self.c.create_sales_order(ctx(), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "approval_required")

    def test_garbage_and_forged_token(self):
        for tok in ("garbage", "v1|a|b|9999999999|deadbeef", "v1|a|b|notint|x"):
            res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE,
                                            "PO-1", idempotency_key="k")
            self.assertFalse(res.ok, tok)
            self.assertIn(res.reason, ("approval_malformed", "approval_signature_invalid"))
        self.assertEqual(self.c.sales_orders, {})

    def test_token_signed_with_wrong_secret(self):
        tok = issue_approval_token(b"other-secret", "u-approver",
                                   compute_action_hash("create_sales_order", so_args()), now=NOW)
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "approval_signature_invalid")

    def test_token_bound_to_arguments(self):
        tok = token_for("create_sales_order", so_args())  # approved qty 10
        tampered = [{"part_no": "BR-12345", "qty": 10000}]
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", tampered, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "approval_signature_invalid")

    def test_token_bound_to_tool(self):
        tok = token_for("create_purchase_request", {"items": ITEMS, "urgency": "normal"})
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertFalse(res.ok)

    def test_expired_token(self):
        tok = token_for("create_sales_order", so_args(), ttl_seconds=60)
        c = MockErpConnector(SECRET, clock=lambda: NOW + timedelta(seconds=61))
        res = c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                   idempotency_key="k")
        self.assertEqual(res.reason, "approval_expired")
        self.assertFalse(res.ok)

    def test_self_approval_refused(self):
        tok = token_for("create_sales_order", so_args(), approver="u-requester")
        res = self.c.create_sales_order(ctx(token=tok), "C-A001", ITEMS, FUTURE, "PO-1",
                                        idempotency_key="k")
        self.assertRefused(res, "self_approval")

    def test_role_not_permitted_even_with_valid_token(self):
        tok = token_for("create_sales_order", so_args())
        res = self.c.create_sales_order(ctx(role="operator", token=tok), "C-A001", ITEMS,
                                        FUTURE, "PO-1", idempotency_key="k")
        self.assertRefused(res, "role_not_permitted")

    def test_valid_token_commits(self):
        res = approved_so(self.c)
        self.assertTrue(res.ok)
        self.assertEqual(res.status, "committed")
        self.assertEqual(res.approver_id, "u-approver")
        self.assertIn(res.record_id, self.c.sales_orders)

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
        self.assertEqual((c.sales_orders, c.purchase_requests, c.movements), ({}, {}, []))
        self.assertEqual(c.get_inventory(ctx(), "BR-12345").on_hand, Decimal("420"))

    def test_verify_approval_never_raises_on_junk(self):
        for tok in (None, "", "x", "v1|||", "v1|a|b|c|d|e", 123):
            d = self.c.verify_approval(tok, "sha256:00")
            self.assertFalse(d.valid)

    def test_idempotency_key_validation(self):
        for bad in ("", "  ", "x" * 129, "a\nb"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                self.c.create_sales_order(ctx(), "C-A001", ITEMS, FUTURE, "PO-1",
                                          idempotency_key=bad)


class Idempotency(unittest.TestCase):
    def setUp(self):
        self.c = make()

    def test_same_key_same_result_no_duplicate(self):
        r1 = approved_so(self.c, "k-1")
        r2 = approved_so(self.c, "k-1")
        self.assertEqual(r1.status, "committed")
        self.assertEqual(r2.status, "replayed")
        self.assertTrue(r2.ok)
        self.assertEqual(r1.record_id, r2.record_id)
        self.assertEqual(len(self.c.sales_orders), 1)

    def test_different_key_creates_new_record(self):
        r1 = approved_so(self.c, "k-1")
        r2 = approved_so(self.c, "k-2")
        self.assertNotEqual(r1.record_id, r2.record_id)
        self.assertEqual(len(self.c.sales_orders), 2)

    def test_same_key_different_arguments_is_conflict(self):
        approved_so(self.c, "k-1")
        r = approved_so(self.c, "k-1", items=[{"part_no": "BR-12345", "qty": 99}])
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "idempotency_key_conflict")
        self.assertEqual(len(self.c.sales_orders), 1)

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

    def test_create_then_close_sales_order(self):
        so = approved_so(self.c, "k-1").record_id
        args = {"so_id": so, "shipment_doc": {"doc": "S-1"}}
        c = ctx(token=token_for("close_sales_order", args))
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-1")
        self.assertTrue(r.ok)
        self.assertEqual(self.c.sales_orders[so]["status"], "closed")
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-1")
        self.assertEqual(r.status, "replayed")
        r = self.c.close_sales_order(c, so, {"doc": "S-1"}, idempotency_key="close-2")
        self.assertEqual(r.reason, "validation:sales_order_not_open")

    def test_purchase_request(self):
        args = {"items": ITEMS, "urgency": "urgent"}
        c = ctx("inventory-manager", token=token_for("create_purchase_request", args))
        r = self.c.create_purchase_request(c, ITEMS, "urgent", idempotency_key="pr-1")
        self.assertTrue(r.ok)
        self.assertIn(r.record_id, self.c.purchase_requests)


class Audit(unittest.TestCase):
    def test_write_result_audit_fields_committed_and_refused(self):
        c = make()
        ok = approved_so(c)
        refused = c.create_sales_order(ctx(rid="req-r"), "C-A001", ITEMS, FUTURE, "PO-1",
                                       idempotency_key="k-r")
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
        self.assertEqual(refused.audit_record()["decision"], "deny")
        self.assertEqual(refused.audit_record()["deny_reason"], "approval_required")

    def test_every_call_is_audited_and_token_never_logged(self):
        c = make()
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

    def test_action_hash_is_stable_and_excludes_key(self):
        a = compute_action_hash("t", {"x": Decimal("1"), "y": [1, 2]})
        b = compute_action_hash("t", {"y": [1, 2], "x": Decimal("1")})
        self.assertEqual(a, b)
        self.assertNotEqual(a, compute_action_hash("t2", {"x": Decimal("1"), "y": [1, 2]}))

    def test_mock_data_is_synthetic_json(self):
        text = (ERP_DIR / "mock-data" / "erp_mock.json").read_text(encoding="utf-8")
        data = json.loads(text)
        self.assertTrue(data["customers"])
        self.assertIn("example.invalid", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
