"""
ERP Connector — Interface contract.

This file defines the interface that any ERP connector implementation must
fulfill so that manufacturing-skill agents can call ERP-related tools
without knowing the specific ERP brand.

Implementations live in sibling repos / dirs:
    erp-connector-sap/
    erp-connector-tiptop/
    erp-connector-business-one/
    ...

This is NOT a runnable server. It's the contract. A reference in-memory
implementation for tests and demos lives in ``mock_connector.py``
(synthetic data only, never connect it to a real ERP).

Requires Python 3.10+ (PEP 604 unions). Standard library only.

Design rules every implementation must follow
---------------------------------------------
1. Every tool takes a typed ``CallContext`` as its first argument. The old
   free-string ``operator`` is gone: a string the caller types can be forged,
   a ``CallContext`` is built by the gateway from authenticated identity.
2. Every write tool takes a required keyword-only ``idempotency_key`` and
   must call ``authorize_write()`` (which calls ``verify_approval()``) BEFORE
   touching the ERP. Same key + same arguments => same result, no duplicate.
3. Every list/query tool takes ``max_rows`` (default 200, hard cap 1000) and
   ``fields`` (allowlist). Price and customer-contact fields are masked
   unless the caller's role is granted them (see ``DEFAULT_ROLE_GRANTS``).
4. Every call (read or write, allowed or refused) is audit-logged with the
   CallContext (see ``ErpConnector.record_audit``). Never log
   ``approval_token``.
5. Timestamps are timezone-aware; quantities and money are ``Decimal``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import IntEnum
from typing import Any, Iterable, Mapping

# ─── Limits & masking policy ────────────────────────────────

DEFAULT_MAX_ROWS = 200
HARD_MAX_ROWS = 1000
MAX_IDEMPOTENCY_KEY_LEN = 128

# 敏感欄位群組。"price" 涵蓋所有金額類欄位（成本、費率、採購單價、信用額度）；
# "customer_contact" 涵蓋客戶聯絡人個資。
PRICE_FIELDS: frozenset[str] = frozenset(
    {
        "standard_cost",
        "hourly_rate",
        "setup_rate",
        "unit_price",
        "credit_limit",
        "credit_used",
        "available",
    }
)
CONTACT_FIELDS: frozenset[str] = frozenset(
    {"contact_name", "contact_phone", "contact_email"}
)
SENSITIVE_GROUPS: Mapping[str, frozenset[str]] = {
    "price": PRICE_FIELDS,
    "customer_contact": CONTACT_FIELDS,
}

# Default: which sensitive groups each role may see. Unknown role => nothing
# (deny by default). Deployments override by setting ``role_grants`` on their
# connector; narrowing is always safe, widening needs a security review.
DEFAULT_ROLE_GRANTS: Mapping[str, frozenset[str]] = {
    "quote-specialist": frozenset({"price"}),
    "sales-coordinator": frozenset({"price", "customer_contact"}),
    "inventory-manager": frozenset(),
    "operator": frozenset(),
}

# Default role allowlist per write tool (same roles as README). A role that is
# not listed is refused before approval is even checked.
DEFAULT_WRITE_ROLES: Mapping[str, frozenset[str]] = {
    "create_sales_order": frozenset({"sales-coordinator"}),
    "create_purchase_request": frozenset({"inventory-manager"}),
    "update_inventory_movement": frozenset({"inventory-manager", "operator"}),
    "close_sales_order": frozenset({"sales-coordinator"}),
}


def clamp_max_rows(max_rows: int | None) -> int:
    """Normalise a ``max_rows`` argument: None -> 200, above 1000 -> 1000.

    Raises ValueError for non-integers (bool included) and values < 1.
    """
    if max_rows is None:
        return DEFAULT_MAX_ROWS
    if isinstance(max_rows, bool) or not isinstance(max_rows, int):
        raise ValueError("max_rows must be an int")
    if max_rows < 1:
        raise ValueError("max_rows must be >= 1")
    return min(max_rows, HARD_MAX_ROWS)


def masked_field_names(
    role: str, role_grants: Mapping[str, Iterable[str]] | None = None
) -> frozenset[str]:
    """Field names that must be hidden from ``role`` (deny by default)."""
    grants = DEFAULT_ROLE_GRANTS if role_grants is None else role_grants
    granted = set(grants.get(role, ()))
    hidden: set[str] = set()
    for group, names in SENSITIVE_GROUPS.items():
        if group not in granted:
            hidden |= names
    return frozenset(hidden)


def project_fields(
    record: Mapping[str, Any],
    fields: Iterable[str] | None,
    masked: frozenset[str],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Apply the ``fields`` allowlist and masking to one record.

    ``fields=None`` returns every non-masked field. A requested field that is
    masked is dropped (and reported), never returned. A requested field that
    does not exist raises ValueError, so typos are not silently ignored.
    Returns (row, names_of_fields_that_were_hidden).
    """
    if fields is None:
        wanted = list(record)
    else:
        if isinstance(fields, str):
            raise ValueError("fields must be a list of names, not a string")
        wanted = list(fields)
        unknown = [f for f in wanted if f not in record]
        if unknown:
            raise ValueError(f"unknown fields: {sorted(unknown)}")
    row = {f: record[f] for f in wanted if f not in masked}
    hidden = tuple(sorted(f for f in wanted if f in masked))
    return row, hidden


def canonical_json(obj: Any) -> str:
    """Deterministic JSON used for action hashes (sorted keys, no spaces)."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


def compute_action_hash(tool: str, args: Mapping[str, Any]) -> str:
    """``sha256:<hex>`` over the tool name and its business arguments.

    ``ctx`` and ``idempotency_key`` are NOT part of the hash: the approver
    approves *what* is done, and a retry with a new key must not need a new
    approval of identical content. Decimal/datetime are stringified, so use
    the same types the gateway used when it computed ``args_hash``.
    """
    payload = canonical_json({"tool": tool, "args": dict(args)})
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ─── Call context ───────────────────────────────────────────


class Tier(IntEnum):
    """Data classification tier of the conversation/channel (T0 lowest)."""

    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3


@dataclass(frozen=True)
class CallContext:
    """Who is calling, from where, and under which authority.

    Built by the gateway from authenticated identity — never from text the
    user (or the model) typed. Passed as the first argument to every tool.
    """

    operator_id: str  # stable id of the human requester (not a display name)
    role: str  # e.g. "sales-coordinator"; drives masking and write rights
    channel: str  # source channel / surface, e.g. "chat:ch-qa-floor", "cli"
    request_id: str  # unique per request; correlates gateway and ERP logs
    classification: Tier  # T0–T3 tier of the originating channel
    timestamp: datetime  # timezone-aware time the request was made
    # Opaque approval token issued by the approval service (for the chat
    # gateway in infra/chat-gateway/ this is an HMAC-signed token minted after
    # a human clicks approve). Required by write tools. Hidden from repr().
    approval_token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        for name in ("operator_id", "role", "channel", "request_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"CallContext.{name} must be a non-empty string")
        if not isinstance(self.classification, Tier):
            raise ValueError("CallContext.classification must be a Tier")
        if (
            not isinstance(self.timestamp, datetime)
            or self.timestamp.tzinfo is None
            or self.timestamp.utcoffset() is None
        ):
            raise ValueError("CallContext.timestamp must be timezone-aware")
        if self.approval_token is not None and not isinstance(
            self.approval_token, str
        ):
            raise ValueError("CallContext.approval_token must be str or None")

    def audit_fields(self) -> dict[str, Any]:
        """Context fields safe to log. The token itself is never included."""
        return {
            "operator_id": self.operator_id,
            "role": self.role,
            "channel": self.channel,
            "request_id": self.request_id,
            "classification": self.classification.name,
            "ctx_ts": self.timestamp.astimezone(timezone.utc).isoformat(),
            "has_approval_token": self.approval_token is not None,
        }


# ─── Result types ───────────────────────────────────────────


@dataclass
class CustomerMaster:
    id: str
    name: str
    grade: str  # "A" | "B" | "C"
    credit_limit: Decimal | None  # None when masked
    credit_used: Decimal | None  # None when masked
    payment_terms: str  # e.g. "T/T 30", "Net 60"
    industry: str | None = None
    requires_iatf: bool = False  # 汽車業客戶通常 True
    contact_name: str | None = None  # None when masked
    contact_phone: str | None = None  # None when masked
    contact_email: str | None = None  # None when masked
    masked_fields: tuple[str, ...] = ()  # fields hidden from this role


@dataclass
class PartMaster:
    part_no: str
    name: str
    spec: str
    standard_cost: Decimal | None  # None when masked
    unit: str  # "PCS" | "KG" | "M"
    abc_class: str  # "A" | "B" | "C"
    masked_fields: tuple[str, ...] = ()


@dataclass
class InventorySnapshot:
    part_no: str
    on_hand: Decimal
    in_transit: Decimal
    safety_stock: Decimal
    abc_class: str
    last_movement_at: datetime  # timezone-aware


@dataclass
class MachineRate:
    machine: str
    hourly_rate: Decimal | None  # 含人工 + 折舊 + 管理 + 水電; None when masked
    setup_rate: Decimal | None  # None when masked
    valid_from: datetime  # timezone-aware
    valid_to: datetime | None = None
    masked_fields: tuple[str, ...] = ()


@dataclass
class PurchasePrice:
    part_no: str
    unit_price: Decimal | None  # None when masked
    currency: str
    as_of: datetime  # timezone-aware
    masked_fields: tuple[str, ...] = ()


@dataclass
class CreditStatus:
    customer_id: str
    credit_limit: Decimal | None  # None when masked
    credit_used: Decimal | None  # None when masked
    available: Decimal | None  # None when masked
    warnings: tuple[str, ...] = ()
    masked_fields: tuple[str, ...] = ()


@dataclass
class ListResult:
    """Result of a list/query tool.

    ``rows`` are plain dicts so the ``fields`` allowlist can be applied.
    ``truncated`` is True when more rows matched than ``max_rows_applied``.
    """

    rows: list[dict[str, Any]]
    total_matched: int
    max_rows_applied: int
    truncated: bool
    fields: tuple[str, ...]  # field names actually present in each row
    masked_fields: tuple[str, ...] = ()  # requested/sensitive fields withheld


@dataclass(frozen=True)
class ApprovalDecision:
    """Outcome of ``verify_approval``. A refusal is a value, not an exception."""

    valid: bool
    approver_id: str | None = None
    approval_id: str | None = None
    reason: str | None = None  # machine-readable, set when not valid


@dataclass
class WriteResult:
    """Result of every write tool. Replaces the old bare ``str`` / ``bool``.

    ``status`` is one of "committed", "replayed" (same idempotency key seen
    before; the original result is returned, nothing is written again) or
    "refused" (nothing was written; see ``reason``). ``ok`` is True for
    committed and replayed.
    """

    ok: bool
    status: str  # "committed" | "replayed" | "refused"
    tool: str
    idempotency_key: str
    action_hash: str
    operator_id: str
    role: str
    channel: str
    request_id: str
    classification: str  # "T0".."T3"
    timestamp: datetime  # server time of the decision, timezone-aware
    record_id: str | None = None  # SO id / PR id / movement id, when committed
    approver_id: str | None = None
    approval_id: str | None = None
    reason: str | None = None  # why refused

    def audit_record(self) -> dict[str, Any]:
        """Audit fields (SEC-08 shape). Never contains the approval token."""
        return {
            "v": 1,
            "ts": self.timestamp.astimezone(timezone.utc).isoformat(),
            "tool": self.tool,
            "access": "write",
            "operator_id": self.operator_id,
            "role": self.role,
            "channel": self.channel,
            "request_id": self.request_id,
            "classification": self.classification,
            "approver": self.approver_id,
            "approval_id": self.approval_id,
            "args_hash": self.action_hash,
            "idempotency_key": self.idempotency_key,
            "record_id": self.record_id,
            "decision": "allow" if self.ok else "deny",
            "status": self.status,
            "deny_reason": self.reason,
        }


# ─── The contract ───────────────────────────────────────────

_audit_logger = logging.getLogger("erp_connector.audit")


class ErpConnector(ABC):
    """Implement this for your ERP.

    Python 3.10+. Every abstract tool takes ``ctx: CallContext`` first.
    ``verify_approval`` is the only abstract hook without ``ctx`` (it checks a
    token, not a caller).
    """

    # Overridable per deployment (class attribute or set in __init__).
    role_grants: Mapping[str, Iterable[str]] = DEFAULT_ROLE_GRANTS
    write_roles: Mapping[str, Iterable[str]] = DEFAULT_WRITE_ROLES

    # ─── Approval & audit hooks ─────────────────────────────

    @abstractmethod
    def verify_approval(
        self, token: str | None, action_hash: str
    ) -> ApprovalDecision:
        """Verify an approval token against the hash of the action.

        MUST be called (via ``authorize_write``) before ANY write. The token
        is opaque and issued by an approval service outside the ERP; the chat
        gateway in ``infra/chat-gateway/`` issues HMAC-signed tokens after a
        human approves in an interactive element. A conforming check:

        - the signature/MAC is valid (constant-time comparison);
        - it is bound to exactly this ``action_hash`` (no token reuse for a
          different action, which prevents TOCTOU swaps);
        - it has not expired;
        - it names an approver (``approver_id``).

        Must never raise for a bad token; return ``ApprovalDecision(False,
        reason=...)`` instead. Anything not verifiable is a refusal.
        """

    def record_audit(self, event: dict[str, Any]) -> None:
        """Persist one audit event. Default: one JSON line on the
        ``erp_connector.audit`` logger. Override to write to your append-only
        audit store. Called for every tool call, allowed or refused.
        """
        _audit_logger.info(canonical_json(event))

    # ─── Concrete helpers implementations should use ────────

    def audit_call(
        self,
        ctx: CallContext,
        tool: str,
        access: str,
        decision: str,
        **extra: Any,
    ) -> None:
        """Build and record an audit event from a CallContext."""
        event = {
            "v": 1,
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "access": access,
            "decision": decision,
            **ctx.audit_fields(),
            **extra,
        }
        self.record_audit(event)

    def masked_for(self, ctx: CallContext) -> frozenset[str]:
        """Sensitive field names hidden from ``ctx.role``."""
        return masked_field_names(ctx.role, self.role_grants)

    def authorize_write(
        self, ctx: CallContext, tool: str, args: Mapping[str, Any]
    ) -> tuple[ApprovalDecision, str]:
        """Gate for every write tool. Returns (decision, action_hash).

        Order: role allowed for this tool -> token present -> verify_approval
        -> approver differs from requester (dual control). Call this first in
        every write; if ``decision.valid`` is False, return a refused
        ``WriteResult`` and do not touch the ERP.
        """
        action_hash = compute_action_hash(tool, args)
        allowed = set(self.write_roles.get(tool, ()))
        if ctx.role not in allowed:
            return ApprovalDecision(False, reason="role_not_permitted"), action_hash
        if not ctx.approval_token:
            return ApprovalDecision(False, reason="approval_required"), action_hash
        decision = self.verify_approval(ctx.approval_token, action_hash)
        if not decision.valid:
            reason = decision.reason or "approval_invalid"
            return ApprovalDecision(False, reason=reason), action_hash
        if not decision.approver_id or decision.approver_id == ctx.operator_id:
            return ApprovalDecision(False, reason="self_approval"), action_hash
        return decision, action_hash

    def make_write_result(
        self,
        ctx: CallContext,
        tool: str,
        idempotency_key: str,
        action_hash: str,
        decision: ApprovalDecision,
        *,
        status: str,
        record_id: str | None = None,
        reason: str | None = None,
        timestamp: datetime | None = None,
    ) -> WriteResult:
        """Build a WriteResult with all audit fields and record the audit."""
        result = WriteResult(
            ok=status in ("committed", "replayed"),
            status=status,
            tool=tool,
            idempotency_key=idempotency_key,
            action_hash=action_hash,
            operator_id=ctx.operator_id,
            role=ctx.role,
            channel=ctx.channel,
            request_id=ctx.request_id,
            classification=ctx.classification.name,
            timestamp=timestamp or datetime.now(timezone.utc),
            record_id=record_id,
            approver_id=decision.approver_id,
            approval_id=decision.approval_id,
            reason=reason,
        )
        self.record_audit(result.audit_record())
        return result

    @staticmethod
    def validate_idempotency_key(key: str) -> str:
        """Non-empty, printable, <= 128 chars. Raises ValueError otherwise."""
        if (
            not isinstance(key, str)
            or not key.strip()
            or len(key) > MAX_IDEMPOTENCY_KEY_LEN
            or not key.isprintable()
        ):
            raise ValueError("idempotency_key must be a printable string, 1-128 chars")
        return key

    # ─── Read tools ─────────────────────────────────────────

    @abstractmethod
    def get_customer(
        self, ctx: CallContext, customer_id: str
    ) -> CustomerMaster | None:
        """Credit fields and contact fields are masked per ``ctx.role``."""

    @abstractmethod
    def get_part_master(self, ctx: CallContext, part_no: str) -> PartMaster | None:
        """``standard_cost`` is masked per ``ctx.role``."""

    @abstractmethod
    def get_inventory(
        self, ctx: CallContext, part_no: str
    ) -> InventorySnapshot | None:
        ...

    @abstractmethod
    def get_recent_purchase_price(
        self, ctx: CallContext, part_no: str, days: int = 30
    ) -> PurchasePrice | None:
        """Latest purchase unit price within N days, or None if there is none.

        ``unit_price`` is None (and listed in ``masked_fields``) when the role
        may not see prices, so "no price" and "hidden" stay distinguishable.
        """

    @abstractmethod
    def get_machine_rate(self, ctx: CallContext, machine: str) -> MachineRate | None:
        """Rates are masked per ``ctx.role``."""

    @abstractmethod
    def get_credit_status(
        self, ctx: CallContext, customer_id: str
    ) -> CreditStatus | None:
        """Credit amounts are masked per ``ctx.role``; ``warnings`` are not."""

    # ─── List / query tools (row cap + field allowlist) ─────

    @abstractmethod
    def list_customers(
        self,
        ctx: CallContext,
        *,
        grade: str | None = None,
        max_rows: int | None = None,
        fields: Iterable[str] | None = None,
    ) -> ListResult:
        """Use ``clamp_max_rows`` and ``project_fields``; never return more
        than 1000 rows regardless of the caller's request."""

    @abstractmethod
    def list_parts(
        self,
        ctx: CallContext,
        *,
        abc_class: str | None = None,
        max_rows: int | None = None,
        fields: Iterable[str] | None = None,
    ) -> ListResult:
        ...

    @abstractmethod
    def list_inventory(
        self,
        ctx: CallContext,
        *,
        below_safety_stock: bool = False,
        max_rows: int | None = None,
        fields: Iterable[str] | None = None,
    ) -> ListResult:
        ...

    # ─── Write tools (high-impact, must audit) ──────────────
    #
    # Every write: validate_idempotency_key -> authorize_write (calls
    # verify_approval) -> idempotency lookup -> ERP write -> make_write_result.
    # Refusals return WriteResult(ok=False, status="refused"), never a bare
    # False, so "refused" and "failed" are not conflated.

    @abstractmethod
    def create_sales_order(
        self,
        ctx: CallContext,
        customer_id: str,
        items: list[dict],
        delivery_date: datetime,  # timezone-aware
        po_reference: str,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        """On success ``record_id`` is the SO id."""

    @abstractmethod
    def create_purchase_request(
        self,
        ctx: CallContext,
        items: list[dict],
        urgency: str,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        """On success ``record_id`` is the PR id."""

    @abstractmethod
    def update_inventory_movement(
        self,
        ctx: CallContext,
        part_no: str,
        qty: Decimal,  # Decimal, not float: this is a ledger
        direction: str,  # "in" | "out"
        reference: str,  # e.g. WO ID
        *,
        idempotency_key: str,
    ) -> WriteResult:
        """On success ``record_id`` is the movement id."""

    @abstractmethod
    def close_sales_order(
        self,
        ctx: CallContext,
        so_id: str,
        shipment_doc: dict,
        *,
        idempotency_key: str,
    ) -> WriteResult:
        """On success ``record_id`` is the SO id."""
