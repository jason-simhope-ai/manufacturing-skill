"""
MockErpConnector — reference implementation of ``contract.ErpConnector``.

Purpose: show, in running code, what a conforming connector does and give the
test-suite something to exercise. It keeps everything in memory and loads
SYNTHETIC data from ``mock-data/erp_mock.json``. It is NOT a production
connector: never point it at a real ERP, and never put real customer data in
the JSON.

What it demonstrates
--------------------
- masking of price and customer-contact fields by ``ctx.role``;
- ``max_rows`` default 200 / hard cap 1000, and the ``fields`` allowlist;
- idempotent writes (same key + same arguments -> same record, no duplicate);
- refusal without a valid approval token (role check, token bound to the
  action hash, expiry, approver != requester);
- an audit event for every call, in ``self.audit_log``.

The approval token format below (``issue_approval_token``) is a mock stand-in
for whatever your approval service issues; the contract only requires that
``verify_approval`` validates it and binds it to ``action_hash``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable

from contract import (
    ApprovalDecision,
    CallContext,
    CreditStatus,
    CustomerMaster,
    ErpConnector,
    InventorySnapshot,
    ListResult,
    MachineRate,
    PartMaster,
    PurchasePrice,
    WriteResult,
    clamp_max_rows,
    project_fields,
)

DEFAULT_DATA_PATH = Path(__file__).parent / "mock-data" / "erp_mock.json"


def issue_approval_token(
    secret: bytes,
    approver_id: str,
    action_hash: str,
    *,
    ttl_seconds: int = 900,
    now: datetime | None = None,
    approval_id: str | None = None,
) -> str:
    """Mint a mock approval token: ``v1|approver|approval_id|expiry|mac``.

    Mirrors what an approval service (e.g. the chat gateway) would do after a
    human approves. The MAC covers approver, approval id, expiry and the
    action hash, so the token cannot be reused for a different action.
    """
    now = now or datetime.now(timezone.utc)
    expiry = int((now + timedelta(seconds=ttl_seconds)).timestamp())
    approval_id = approval_id or uuid.uuid4().hex
    mac = _mac(secret, approver_id, approval_id, expiry, action_hash)
    return f"v1|{approver_id}|{approval_id}|{expiry}|{mac}"


def _mac(
    secret: bytes, approver_id: str, approval_id: str, expiry: int, action_hash: str
) -> str:
    msg = f"v1|{approver_id}|{approval_id}|{expiry}|{action_hash}".encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class MockErpConnector(ErpConnector):
    def __init__(
        self,
        approval_secret: bytes,
        data: dict | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not approval_secret:
            raise ValueError("approval_secret must be non-empty")
        self._secret = approval_secret
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        if data is None:
            data = json.loads(DEFAULT_DATA_PATH.read_text(encoding="utf-8"))
        self._customers = {c["id"]: dict(c) for c in data.get("customers", [])}
        self._parts = {p["part_no"]: dict(p) for p in data.get("parts", [])}
        self._inventory = {i["part_no"]: dict(i) for i in data.get("inventory", [])}
        self._rates = {r["machine"]: dict(r) for r in data.get("machine_rates", [])}
        self._prices = [dict(p) for p in data.get("purchase_prices", [])]
        # Write side
        self.sales_orders: dict[str, dict] = {}
        self.purchase_requests: dict[str, dict] = {}
        self.movements: list[dict] = []
        self._idem: dict[tuple[str, str], tuple[str, str]] = {}
        self._lock = threading.Lock()
        self._seq = 0
        # Every call, allowed or refused (see ErpConnector.record_audit)
        self.audit_log: list[dict] = []

    # ─── Hooks ──────────────────────────────────────────────

    def record_audit(self, event: dict[str, Any]) -> None:
        self.audit_log.append(event)

    def verify_approval(self, token: str | None, action_hash: str) -> ApprovalDecision:
        if not token or not isinstance(token, str):
            return ApprovalDecision(False, reason="approval_required")
        parts = token.split("|")
        if len(parts) != 5 or parts[0] != "v1":
            return ApprovalDecision(False, reason="approval_malformed")
        _, approver_id, approval_id, expiry_s, mac = parts
        try:
            expiry = int(expiry_s)
        except ValueError:
            return ApprovalDecision(False, reason="approval_malformed")
        expected = _mac(self._secret, approver_id, approval_id, expiry, action_hash)
        if not hmac.compare_digest(mac, expected):
            # Wrong secret, tampered token, or token for a different action.
            return ApprovalDecision(False, reason="approval_signature_invalid")
        if self._clock().timestamp() > expiry:
            return ApprovalDecision(False, reason="approval_expired")
        return ApprovalDecision(True, approver_id=approver_id, approval_id=approval_id)

    # ─── Read tools ─────────────────────────────────────────

    def get_customer(self, ctx: CallContext, customer_id: str) -> CustomerMaster | None:
        rec = self._customers.get(customer_id)
        if rec is None:
            self.audit_call(ctx, "get_customer", "read", "allow", found=False)
            return None
        masked = self.masked_for(ctx)
        row, hidden = project_fields(self._customer_record(rec), None, masked)
        result = CustomerMaster(
            id=rec["id"],
            name=rec["name"],
            grade=rec["grade"],
            credit_limit=row.get("credit_limit"),
            credit_used=row.get("credit_used"),
            payment_terms=rec["payment_terms"],
            industry=rec.get("industry"),
            requires_iatf=bool(rec.get("requires_iatf", False)),
            contact_name=row.get("contact_name"),
            contact_phone=row.get("contact_phone"),
            contact_email=row.get("contact_email"),
            masked_fields=hidden,
        )
        self.audit_call(ctx, "get_customer", "read", "allow", found=True,
                        masked_fields=list(hidden))
        return result

    def get_part_master(self, ctx: CallContext, part_no: str) -> PartMaster | None:
        rec = self._parts.get(part_no)
        if rec is None:
            self.audit_call(ctx, "get_part_master", "read", "allow", found=False)
            return None
        masked = self.masked_for(ctx)
        hide = "standard_cost" in masked
        result = PartMaster(
            part_no=rec["part_no"],
            name=rec["name"],
            spec=rec["spec"],
            standard_cost=None if hide else _dec(rec["standard_cost"]),
            unit=rec["unit"],
            abc_class=rec["abc_class"],
            masked_fields=("standard_cost",) if hide else (),
        )
        self.audit_call(ctx, "get_part_master", "read", "allow", found=True,
                        masked_fields=list(result.masked_fields))
        return result

    def get_inventory(self, ctx: CallContext, part_no: str) -> InventorySnapshot | None:
        rec = self._inventory.get(part_no)
        self.audit_call(ctx, "get_inventory", "read", "allow", found=rec is not None)
        if rec is None:
            return None
        return self._inventory_snapshot(rec)

    def get_recent_purchase_price(
        self, ctx: CallContext, part_no: str, days: int = 30
    ) -> PurchasePrice | None:
        if isinstance(days, bool) or not isinstance(days, int) or days < 1:
            raise ValueError("days must be a positive int")
        cutoff = self._clock() - timedelta(days=days)
        candidates = [
            p for p in self._prices
            if p["part_no"] == part_no and _dt(p["as_of"]) >= cutoff
        ]
        if not candidates:
            self.audit_call(ctx, "get_recent_purchase_price", "read", "allow", found=False)
            return None
        latest = max(candidates, key=lambda p: _dt(p["as_of"]))
        hide = "unit_price" in self.masked_for(ctx)
        result = PurchasePrice(
            part_no=part_no,
            unit_price=None if hide else _dec(latest["unit_price"]),
            currency=latest["currency"],
            as_of=_dt(latest["as_of"]),
            masked_fields=("unit_price",) if hide else (),
        )
        self.audit_call(ctx, "get_recent_purchase_price", "read", "allow", found=True,
                        masked_fields=list(result.masked_fields))
        return result

    def get_machine_rate(self, ctx: CallContext, machine: str) -> MachineRate | None:
        rec = self._rates.get(machine)
        if rec is None:
            self.audit_call(ctx, "get_machine_rate", "read", "allow", found=False)
            return None
        masked = self.masked_for(ctx)
        hidden = tuple(sorted(f for f in ("hourly_rate", "setup_rate") if f in masked))
        result = MachineRate(
            machine=rec["machine"],
            hourly_rate=None if "hourly_rate" in masked else _dec(rec["hourly_rate"]),
            setup_rate=None if "setup_rate" in masked else _dec(rec["setup_rate"]),
            valid_from=_dt(rec["valid_from"]),
            valid_to=_dt(rec.get("valid_to")),
            masked_fields=hidden,
        )
        self.audit_call(ctx, "get_machine_rate", "read", "allow", found=True,
                        masked_fields=list(hidden))
        return result

    def get_credit_status(self, ctx: CallContext, customer_id: str) -> CreditStatus | None:
        rec = self._customers.get(customer_id)
        if rec is None:
            self.audit_call(ctx, "get_credit_status", "read", "allow", found=False)
            return None
        limit, used = _dec(rec["credit_limit"]), _dec(rec["credit_used"])
        available = limit - used
        warnings = []
        if limit > 0 and used / limit >= Decimal("0.9"):
            warnings.append("credit_used >= 90% of limit")
        masked = self.masked_for(ctx)
        hidden = tuple(
            sorted(f for f in ("credit_limit", "credit_used", "available") if f in masked)
        )
        result = CreditStatus(
            customer_id=customer_id,
            credit_limit=None if "credit_limit" in masked else limit,
            credit_used=None if "credit_used" in masked else used,
            available=None if "available" in masked else available,
            warnings=tuple(warnings),
            masked_fields=hidden,
        )
        self.audit_call(ctx, "get_credit_status", "read", "allow", found=True,
                        masked_fields=list(hidden))
        return result

    # ─── List / query tools ─────────────────────────────────

    def list_customers(
        self,
        ctx: CallContext,
        *,
        grade: str | None = None,
        max_rows: int | None = None,
        fields: Iterable[str] | None = None,
    ) -> ListResult:
        recs = [
            self._customer_record(c)
            for _, c in sorted(self._customers.items())
            if grade is None or c["grade"] == grade
        ]
        return self._list(ctx, "list_customers", recs, max_rows, fields)

    def list_parts(
        self,
        ctx: CallContext,
        *,
        abc_class: str | None = None,
        max_rows: int | None = None,
        fields: Iterable[str] | None = None,
    ) -> ListResult:
        recs = [
            {**p, "standard_cost": _dec(p["standard_cost"])}
            for _, p in sorted(self._parts.items())
            if abc_class is None or p["abc_class"] == abc_class
        ]
        return self._list(ctx, "list_parts", recs, max_rows, fields)

    def list_inventory(
        self,
        ctx: CallContext,
        *,
        below_safety_stock: bool = False,
        max_rows: int | None = None,
        fields: Iterable[str] | None = None,
    ) -> ListResult:
        recs = []
        for _, rec in sorted(self._inventory.items()):
            snap = self._inventory_snapshot(rec)
            if below_safety_stock and not snap.on_hand < snap.safety_stock:
                continue
            recs.append(dict(vars(snap)))
        return self._list(ctx, "list_inventory", recs, max_rows, fields)

    # ─── Write tools ────────────────────────────────────────

    def create_sales_order(
        self,
        ctx: CallContext,
        customer_id: str,
        items: list[dict],
        delivery_date: datetime,
        po_reference: str,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        args = {
            "customer_id": customer_id,
            "items": items,
            "delivery_date": delivery_date.isoformat()
            if isinstance(delivery_date, datetime) else delivery_date,
            "po_reference": po_reference,
        }

        def validate() -> str | None:
            if customer_id not in self._customers:
                return "unknown_customer"
            if not isinstance(delivery_date, datetime) or delivery_date.tzinfo is None:
                return "delivery_date_must_be_timezone_aware"
            return self._validate_items(items)

        def commit() -> str:
            so_id = self._next_id("SO")
            self.sales_orders[so_id] = {
                "so_id": so_id, "customer_id": customer_id, "items": items,
                "delivery_date": args["delivery_date"],
                "po_reference": po_reference, "status": "open",
                "created_by": ctx.operator_id,
            }
            return so_id

        return self._write(ctx, "create_sales_order", args, idempotency_key, validate, commit)

    def create_purchase_request(
        self,
        ctx: CallContext,
        items: list[dict],
        urgency: str,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        args = {"items": items, "urgency": urgency}

        def validate() -> str | None:
            if urgency not in ("normal", "urgent"):
                return "invalid_urgency"
            return self._validate_items(items)

        def commit() -> str:
            pr_id = self._next_id("PR")
            self.purchase_requests[pr_id] = {
                "pr_id": pr_id, "items": items, "urgency": urgency,
                "status": "open", "created_by": ctx.operator_id,
            }
            return pr_id

        return self._write(ctx, "create_purchase_request", args, idempotency_key, validate, commit)

    def update_inventory_movement(
        self,
        ctx: CallContext,
        part_no: str,
        qty: Decimal,
        direction: str,
        reference: str,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        args = {"part_no": part_no, "qty": qty, "direction": direction, "reference": reference}

        def validate() -> str | None:
            if not isinstance(qty, Decimal) or not qty.is_finite() or qty <= 0:
                return "qty_must_be_positive_decimal"
            if direction not in ("in", "out"):
                return "invalid_direction"
            rec = self._inventory.get(part_no)
            if rec is None:
                return "unknown_part"
            if direction == "out" and _dec(rec["on_hand"]) < qty:
                return "insufficient_stock"
            return None

        def commit() -> str:
            mv_id = self._next_id("MV")
            rec = self._inventory[part_no]
            delta = qty if direction == "in" else -qty
            rec["on_hand"] = str(_dec(rec["on_hand"]) + delta)
            rec["last_movement_at"] = self._clock().isoformat()
            self.movements.append({
                "movement_id": mv_id, "part_no": part_no, "qty": qty,
                "direction": direction, "reference": reference,
                "created_by": ctx.operator_id,
            })
            return mv_id

        return self._write(ctx, "update_inventory_movement", args, idempotency_key, validate, commit)

    def close_sales_order(
        self,
        ctx: CallContext,
        so_id: str,
        shipment_doc: dict,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        args = {"so_id": so_id, "shipment_doc": shipment_doc}

        def validate() -> str | None:
            so = self.sales_orders.get(so_id)
            if so is None:
                return "unknown_sales_order"
            if so["status"] != "open":
                return "sales_order_not_open"
            if not isinstance(shipment_doc, dict) or not shipment_doc:
                return "shipment_doc_required"
            return None

        def commit() -> str:
            self.sales_orders[so_id]["status"] = "closed"
            self.sales_orders[so_id]["shipment_doc"] = shipment_doc
            return so_id

        return self._write(ctx, "close_sales_order", args, idempotency_key, validate, commit)

    # ─── Internals ──────────────────────────────────────────

    def _write(
        self,
        ctx: CallContext,
        tool: str,
        args: dict,
        idempotency_key: str,
        validate: Callable[[], str | None],
        commit: Callable[[], str],
    ) -> WriteResult:
        key = self.validate_idempotency_key(idempotency_key)
        decision, action_hash = self.authorize_write(ctx, tool, args)
        if not decision.valid:
            return self.make_write_result(
                ctx, tool, key, action_hash, decision,
                status="refused", reason=decision.reason, timestamp=self._clock(),
            )
        with self._lock:
            seen = self._idem.get((tool, key))
            if seen is not None:
                seen_hash, record_id = seen
                if seen_hash != action_hash:
                    return self.make_write_result(
                        ctx, tool, key, action_hash, decision, status="refused",
                        reason="idempotency_key_conflict", timestamp=self._clock(),
                    )
                return self.make_write_result(
                    ctx, tool, key, action_hash, decision, status="replayed",
                    record_id=record_id, timestamp=self._clock(),
                )
            problem = validate()
            if problem is not None:
                return self.make_write_result(
                    ctx, tool, key, action_hash, decision, status="refused",
                    reason=f"validation:{problem}", timestamp=self._clock(),
                )
            record_id = commit()
            self._idem[(tool, key)] = (action_hash, record_id)
        return self.make_write_result(
            ctx, tool, key, action_hash, decision, status="committed",
            record_id=record_id, timestamp=self._clock(),
        )

    def _list(
        self,
        ctx: CallContext,
        tool: str,
        records: list[dict],
        max_rows: int | None,
        fields: Iterable[str] | None,
    ) -> ListResult:
        cap = clamp_max_rows(max_rows)
        masked = self.masked_for(ctx)
        field_list = list(fields) if fields is not None else None
        rows: list[dict] = []
        hidden: set[str] = set()
        for rec in records[:cap]:
            row, h = project_fields(rec, field_list, masked)
            rows.append(row)
            hidden.update(h)
        present = tuple(rows[0]) if rows else tuple(
            f for f in (field_list or []) if f not in masked
        )
        result = ListResult(
            rows=rows,
            total_matched=len(records),
            max_rows_applied=cap,
            truncated=len(records) > cap,
            fields=present,
            masked_fields=tuple(sorted(hidden)),
        )
        self.audit_call(
            ctx, tool, "read", "allow", rows=len(rows), total_matched=len(records),
            max_rows_applied=cap, masked_fields=list(result.masked_fields),
        )
        return result

    def _customer_record(self, rec: dict) -> dict:
        out = dict(rec)
        out["credit_limit"] = _dec(rec["credit_limit"])
        out["credit_used"] = _dec(rec["credit_used"])
        return out

    def _inventory_snapshot(self, rec: dict) -> InventorySnapshot:
        return InventorySnapshot(
            part_no=rec["part_no"],
            on_hand=_dec(rec["on_hand"]),
            in_transit=_dec(rec["in_transit"]),
            safety_stock=_dec(rec["safety_stock"]),
            abc_class=rec["abc_class"],
            last_movement_at=_dt(rec["last_movement_at"]),
        )

    @staticmethod
    def _validate_items(items: Any) -> str | None:
        if not isinstance(items, list) or not items:
            return "items_required"
        for it in items:
            if not isinstance(it, dict) or not it.get("part_no"):
                return "item_part_no_required"
            try:
                if _dec(it.get("qty")) <= 0:
                    return "item_qty_must_be_positive"
            except (InvalidOperation, TypeError):
                return "item_qty_invalid"
        return None

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-MOCK-{self._seq:05d}"
