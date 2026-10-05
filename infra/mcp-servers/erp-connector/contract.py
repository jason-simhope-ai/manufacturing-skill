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

This is NOT a runnable server (and not an MCP server yet). It's the
contract. A reference in-memory implementation for tests and demos lives in
``mock_connector.py`` (synthetic data only, never connect it to a real ERP).
The conformance tests in ``tests/mcp/test_erp_contract.py``
(``ConformanceSuite``) can be run against your own connector.

Requires Python 3.10+ (PEP 604 unions). Standard library only.

Design rules every implementation must follow
---------------------------------------------
1. Every tool takes a typed ``CallContext`` as its first argument. The old
   free-string ``operator`` is gone: a string the caller types can be forged,
   a ``CallContext`` is built by the trusted host process (the MCP server
   wrapper today, the chat gateway once it executes actions) from
   authenticated identity, never from model or user text.
2. Every write tool takes a required keyword-only ``idempotency_key`` and
   must call ``authorize_write()`` (which calls ``verify_approval()``) BEFORE
   touching the ERP. Same key + same arguments => same result, no duplicate.
   One approval authorises exactly one write: a second write with the same
   ``approval_id`` under a different key is refused
   (``REASON_APPROVAL_ALREADY_USED``).
3. Every list/query tool takes ``max_rows`` (default 200, hard cap 1000) and
   ``fields`` (allowlist). Price and customer-contact fields are masked
   unless the caller's role is granted them (see ``DEFAULT_ROLE_GRANTS``).
4. Every call (read or write, allowed or refused) is audit-logged with the
   CallContext (see ``ErpConnector.record_audit``; the default writes JSON
   lines to stderr). Never log ``approval_token``.
5. Timestamps are timezone-aware (result types reject naive datetimes);
   quantities and money are ``Decimal``, never ``float``.

Approval hash and token (canonical; defined here)
-------------------------------------------------
The approval service does not exist yet: the chat gateway's ``execute()``
path is deferred (gateway spec section 14), so today nothing outside this
directory signs tokens. This module is the single definition the gateway
will adopt when execution lands:

- ``compute_action_hash(tool, args)`` = ``"sha256:" + hex(sha256(utf8(
  json.dumps({"tool": tool, "args": canonical_args(args)}, sort_keys=True,
  separators=(",", ":"), ensure_ascii=False))))``. ``canonical_args`` applies
  the wire rules: numbers (int, Decimal) -> normalised decimal string,
  datetime -> UTC ISO-8601 with ``Z``, float rejected.
- ``issue_approval_token`` / ``verify_approval_token`` define the token
  ``v1|approver_id|approver_role|approval_id|expiry|mac`` with
  ``mac = HMAC-SHA256(secret, "v1|approver_id|approver_role|approval_id|
  expiry|action_hash")`` in lowercase hex.
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
import sys
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone, tzinfo
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

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

# Default roles allowed to APPROVE each write tool (the ``approver_role``
# bound into the approval token). Deny by default: a tool not listed here, or
# an approver whose role is not listed, is refused even with a valid MAC.
# Align these names with the positions your approval service assigns.
DEFAULT_APPROVER_ROLES: Mapping[str, frozenset[str]] = {
    "create_sales_order": frozenset({"sales-manager", "plant-manager"}),
    "create_purchase_request": frozenset({"purchasing-manager", "plant-manager"}),
    "update_inventory_movement": frozenset({"inventory-manager", "plant-manager"}),
    "close_sales_order": frozenset({"sales-manager", "plant-manager"}),
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
    role: str,
    role_grants: Mapping[str, Iterable[str]] | None = None,
    sensitive_groups: Mapping[str, Iterable[str]] | None = None,
) -> frozenset[str]:
    """Field names that must be hidden from ``role`` (deny by default).

    Masking applies to field VALUES. Which records exist (ids, names, part
    numbers in a list) is not masked; restrict list tools by role if that
    matters to you.
    """
    grants = DEFAULT_ROLE_GRANTS if role_grants is None else role_grants
    groups = SENSITIVE_GROUPS if sensitive_groups is None else sensitive_groups
    granted = set(grants.get(role, ()))
    hidden: set[str] = set()
    for group, names in groups.items():
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
    """Deterministic JSON (sorted keys, no spaces). Used for audit lines.

    Lenient (``default=str``) so an audit event never fails to serialise.
    Action hashes do NOT use this; see ``compute_action_hash``.
    """
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )


# ─── Wire representation (action hash + JSON results) ───────


class CanonicalArgsError(ValueError):
    """An argument has no canonical wire form (float, naive datetime, ...)."""


# Bound on |exponent| so "1E+999999999" cannot expand into a huge string.
MAX_DECIMAL_EXPONENT = 100


def decimal_str(value: Decimal | int) -> str:
    """Normalised decimal string: no exponent, no trailing zeros, "-0" -> "0".

    ``10``, ``Decimal("10")``, ``Decimal("10.00")`` and ``Decimal("1E+1")``
    all give ``"10"``; ``Decimal("0.50")`` gives ``"0.5"``. Exact (no context
    rounding). Raises CanonicalArgsError for NaN / Infinity.
    """
    d = Decimal(value)
    if not d.is_finite():
        raise CanonicalArgsError(f"non-finite number {value!r} has no wire form")
    if d and not -MAX_DECIMAL_EXPONENT <= d.adjusted() <= MAX_DECIMAL_EXPONENT:
        raise CanonicalArgsError(f"number {value!r} is out of range")
    sign, digits, exp = d.as_tuple()
    digits = list(digits)
    while len(digits) > 1 and digits[-1] == 0 and exp < 0:
        digits.pop()
        exp += 1
    if digits == [0]:
        return "0"
    if exp > 0:  # 1E+3 -> 1000
        digits += [0] * exp
        exp = 0
    return format(Decimal((sign, tuple(digits), exp)), "f")


def utc_iso(value: datetime) -> str:
    """ISO-8601 in UTC with a ``Z`` suffix. Naive datetimes are rejected."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise CanonicalArgsError(
            "naive datetime has no wire form; attach the ERP's timezone first "
            "(see aware())"
        )
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _wire(value: Any, path: str, *, numbers_as_str: bool) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, Enum):  # Tier.T2 -> "T2"
        return value.name
    if isinstance(value, float):
        raise CanonicalArgsError(
            f"float at {path} is not allowed (quantities and amounts are "
            "Decimal): pass Decimal(...) or a string, and parse incoming JSON "
            "with json.loads(..., parse_float=Decimal)"
        )
    if isinstance(value, int):
        return decimal_str(value) if numbers_as_str else value
    if isinstance(value, Decimal):
        return decimal_str(value)
    if isinstance(value, datetime):
        return utc_iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalArgsError(f"non-string key {k!r} at {path}")
            out[k] = _wire(v, f"{path}.{k}", numbers_as_str=numbers_as_str)
        return out
    if isinstance(value, (list, tuple)):
        return [
            _wire(v, f"{path}[{i}]", numbers_as_str=numbers_as_str)
            for i, v in enumerate(value)
        ]
    raise CanonicalArgsError(
        f"{type(value).__name__} at {path} has no wire form"
    )


def canonical_args(args: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the wire rules to tool arguments before hashing.

    - int and Decimal -> normalised decimal string (``decimal_str``), so
      ``10``, ``Decimal("10")`` and ``Decimal("10.00")`` hash the same;
    - float -> CanonicalArgsError (never guess a ledger quantity);
    - datetime -> UTC ISO-8601 with ``Z`` (naive -> CanonicalArgsError);
      date -> ``YYYY-MM-DD``;
    - tuple -> list; mappings must have str keys; Enum -> its name;
    - str, bool and None are kept as is (a string is hashed verbatim:
      ``"10.00"`` stays ``"10.00"``; send quantities as numbers/Decimal).
    """
    if not isinstance(args, Mapping):
        raise CanonicalArgsError("args must be a mapping")
    return _wire(args, "args", numbers_as_str=True)


def compute_action_hash(tool: str, args: Mapping[str, Any]) -> str:
    """``sha256:<hex>`` over the tool name and its canonical arguments.

    Exactly: sha256 of the UTF-8 bytes of ``json.dumps({"tool": tool,
    "args": canonical_args(args)}, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False)``, lowercase hex, prefixed ``sha256:``. No
    ``default=``: anything ``canonical_args`` cannot represent raises
    CanonicalArgsError instead of being stringified.

    ``ctx`` and ``idempotency_key`` are NOT part of the hash: the approver
    approves *what* is done. A retry of the same write reuses its key; the
    single-use rule (one approval -> one write) is enforced on
    ``approval_id``, not here.
    """
    if not isinstance(tool, str) or not tool:
        raise CanonicalArgsError("tool must be a non-empty string")
    payload = json.dumps(
        {"tool": tool, "args": canonical_args(args)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def to_jsonable(obj: Any) -> Any:
    """Convert a result (dataclass, ListResult rows, dicts, lists) to plain
    JSON types: Decimal -> normalised decimal string, datetime -> UTC
    ISO-8601 ``Z``, tuple -> list, Enum -> name, nested dataclasses -> dict.
    ints stay JSON numbers; float raises CanonicalArgsError.

    ``json.dumps(to_jsonable(result), ensure_ascii=False)`` is the supported
    way to put a result on the wire (MCP tool output, logs).
    """
    return _wire(obj, "result", numbers_as_str=False)


def aware(value: datetime, tz: tzinfo | str) -> datetime:
    """Attach ``tz`` to a naive datetime read from the ERP (e.g. a SQL view
    that stores local time). ``tz`` is a tzinfo or an IANA name such as
    ``"Asia/Taipei"``. Already-aware values are returned unchanged.
    """
    if not isinstance(value, datetime):
        raise TypeError("aware() expects a datetime")
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value
    zone = ZoneInfo(tz) if isinstance(tz, str) else tz
    return value.replace(tzinfo=zone)


def _require_aware(owner: str, name: str, value: Any, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(
            f"{owner}.{name} must be a timezone-aware datetime (use aware())"
        )


# ─── Approval token (canonical format) ──────────────────────

APPROVAL_TOKEN_VERSION = "v1"
DEFAULT_APPROVAL_TTL_SECONDS = 900

# Refusal reasons (``WriteResult.reason`` / ``ApprovalDecision.reason``).
REASON_ROLE_NOT_PERMITTED = "role_not_permitted"
REASON_APPROVAL_REQUIRED = "approval_required"
REASON_APPROVAL_MALFORMED = "approval_malformed"
REASON_APPROVAL_SIGNATURE_INVALID = "approval_signature_invalid"
REASON_APPROVAL_EXPIRED = "approval_expired"
REASON_SELF_APPROVAL = "self_approval"
REASON_APPROVER_ROLE_NOT_PERMITTED = "approver_role_not_permitted"
REASON_APPROVAL_ALREADY_USED = "approval_already_used"
REASON_IDEMPOTENCY_KEY_CONFLICT = "idempotency_key_conflict"


def _token_field_ok(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and "|" not in value
        and value.isprintable()
    )


def _token_mac(
    secret: bytes,
    approver_id: str,
    approver_role: str,
    approval_id: str,
    expiry: int,
    action_hash: str,
) -> str:
    msg = (
        f"{APPROVAL_TOKEN_VERSION}|{approver_id}|{approver_role}|{approval_id}"
        f"|{expiry}|{action_hash}"
    ).encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def issue_approval_token(
    secret: bytes,
    approver_id: str,
    action_hash: str,
    *,
    approver_role: str,
    ttl_seconds: int = DEFAULT_APPROVAL_TTL_SECONDS,
    now: datetime | None = None,
    approval_id: str | None = None,
) -> str:
    """Mint ``v1|approver_id|approver_role|approval_id|expiry|mac``.

    Called by the approval service after a human approves (the chat gateway
    will call this when its execute path lands; until then only tests and
    the mock use it). ``expiry`` is integer Unix seconds; ``approval_id`` is
    unique per approval and is what the connector consumes on commit.
    """
    if not secret:
        raise ValueError("secret must be non-empty")
    approval_id = approval_id or uuid.uuid4().hex
    for name, value in (
        ("approver_id", approver_id),
        ("approver_role", approver_role),
        ("approval_id", approval_id),
    ):
        if not _token_field_ok(value):
            raise ValueError(f"{name} must be a printable string without '|'")
    if not isinstance(action_hash, str) or not action_hash.startswith("sha256:"):
        raise ValueError("action_hash must come from compute_action_hash()")
    now = now or datetime.now(timezone.utc)
    expiry = int((now + timedelta(seconds=ttl_seconds)).timestamp())
    mac = _token_mac(secret, approver_id, approver_role, approval_id, expiry, action_hash)
    return (
        f"{APPROVAL_TOKEN_VERSION}|{approver_id}|{approver_role}|{approval_id}"
        f"|{expiry}|{mac}"
    )


def verify_approval_token(
    secret: bytes, token: Any, action_hash: str, *, now: datetime
) -> "ApprovalDecision":
    """Reference ``verify_approval`` for the canonical token. Never raises.

    Checks shape, HMAC (constant time, bound to ``action_hash``) and expiry
    against ``now``. Single use and approver role are checked by
    ``authorize_write`` and the write path, not here.
    """
    if not token or not isinstance(token, str):
        return ApprovalDecision(False, reason=REASON_APPROVAL_REQUIRED)
    parts = token.split("|")
    if len(parts) != 6 or parts[0] != APPROVAL_TOKEN_VERSION:
        return ApprovalDecision(False, reason=REASON_APPROVAL_MALFORMED)
    _, approver_id, approver_role, approval_id, expiry_s, mac = parts
    if not all(_token_field_ok(v) for v in (approver_id, approver_role, approval_id)):
        return ApprovalDecision(False, reason=REASON_APPROVAL_MALFORMED)
    if not expiry_s.isdigit() or not expiry_s.isascii():
        return ApprovalDecision(False, reason=REASON_APPROVAL_MALFORMED)
    expiry = int(expiry_s)
    expected = _token_mac(
        secret, approver_id, approver_role, approval_id, expiry, action_hash
    )
    if not hmac.compare_digest(mac.encode("utf-8"), expected.encode("utf-8")):
        # Wrong secret, tampered token, or token for a different action.
        return ApprovalDecision(False, reason=REASON_APPROVAL_SIGNATURE_INVALID)
    if now.timestamp() > expiry:
        return ApprovalDecision(False, reason=REASON_APPROVAL_EXPIRED)
    return ApprovalDecision(
        True,
        approver_id=approver_id,
        approval_id=approval_id,
        approver_role=approver_role,
    )


# ─── Call context ───────────────────────────────────────────


class Tier(IntEnum):
    """Data classification tier of the conversation/channel (T0 lowest).

    Same labels as the chat gateway's string tiers: ``Tier["T2"]`` parses a
    gateway label, ``tier.name`` gives it back. The gateway refuses to load
    T3 channels; a connector may additionally refuse writes from T3.
    """

    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3


@dataclass(frozen=True)
class CallContext:
    """Who is calling, from where, and under which authority.

    Built by the trusted host process from authenticated identity — never
    from text the user (or the model) typed. Today that host is whatever
    wraps the connector (for a single-user stdio MCP server: settings fixed
    at start-up, a convenience, not a security boundary); once the chat
    gateway executes actions it builds the context per request. Passed as the
    first argument to every tool.
    """

    # Stable employee id of the human requester (never a display name). The
    # gateway keeps only role + an HMAC ref in its own audit; it maps the
    # authenticated user to the employee id via its identities roster.
    operator_id: str
    role: str  # e.g. "sales-coordinator"; drives masking and write rights
    channel: str  # source channel / surface, e.g. "chat:ch-qa-floor", "cli"
    # Unique per request; set it to the gateway's audit ``event_id`` so the
    # gateway hash chain and the ERP audit join on one key.
    request_id: str
    classification: Tier  # T0–T3 tier of the originating channel
    timestamp: datetime  # timezone-aware time the request was made
    # Opaque approval token in the canonical format of
    # ``issue_approval_token`` (HMAC-signed after a human approves). Nothing
    # issues it in production yet: the chat gateway will once its execute
    # path lands. Required by write tools. Hidden from repr().
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

    def __post_init__(self) -> None:
        _require_aware("InventorySnapshot", "last_movement_at", self.last_movement_at)


@dataclass
class MachineRate:
    machine: str
    hourly_rate: Decimal | None  # 含人工 + 折舊 + 管理 + 水電; None when masked
    setup_rate: Decimal | None  # None when masked
    valid_from: datetime  # timezone-aware
    valid_to: datetime | None = None
    masked_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_aware("MachineRate", "valid_from", self.valid_from)
        _require_aware("MachineRate", "valid_to", self.valid_to, optional=True)


@dataclass
class PurchasePrice:
    part_no: str
    unit_price: Decimal | None  # None when masked
    currency: str
    as_of: datetime  # timezone-aware
    masked_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_aware("PurchasePrice", "as_of", self.as_of)


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
    ``truncated`` (alias ``has_more``) is True when more rows matched than
    ``max_rows_applied``; fetch ``cap + 1`` rows with SQL ``LIMIT`` to know
    it. ``total_matched`` is the full match count, or None when counting
    would need an expensive ``COUNT(*)`` the connector chose not to run.
    """

    rows: list[dict[str, Any]]
    total_matched: int | None
    max_rows_applied: int
    truncated: bool
    fields: tuple[str, ...]  # field names actually present in each row
    masked_fields: tuple[str, ...] = ()  # requested/sensitive fields withheld

    def __post_init__(self) -> None:
        if self.total_matched is not None and (
            isinstance(self.total_matched, bool)
            or not isinstance(self.total_matched, int)
            or self.total_matched < 0
        ):
            raise ValueError("ListResult.total_matched must be an int >= 0 or None")

    @property
    def has_more(self) -> bool:
        """True when rows beyond ``max_rows_applied`` exist (= ``truncated``)."""
        return self.truncated


@dataclass(frozen=True)
class ApprovalDecision:
    """Outcome of ``verify_approval``. A refusal is a value, not an exception."""

    valid: bool
    approver_id: str | None = None
    approval_id: str | None = None  # consumed on the first committed write
    reason: str | None = None  # machine-readable, set when not valid
    approver_role: str | None = None  # checked against ``approver_roles``


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
    approver_role: str | None = None

    def __post_init__(self) -> None:
        _require_aware("WriteResult", "timestamp", self.timestamp)

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
            "approver_role": self.approver_role,
            "approval_id": self.approval_id,
            "args_hash": self.action_hash,
            "idempotency_key": self.idempotency_key,
            "record_id": self.record_id,
            "decision": "allow" if self.ok else "deny",
            "status": self.status,
            "deny_reason": self.reason,
        }


# ─── The contract ───────────────────────────────────────────


class ErpConnector(ABC):
    """Implement this for your ERP.

    Python 3.10+. Every abstract tool takes ``ctx: CallContext`` first.
    ``verify_approval`` is the only abstract hook without ``ctx`` (it checks a
    token, not a caller).
    """

    # Overridable per deployment (class attribute or set in __init__).
    role_grants: Mapping[str, Iterable[str]] = DEFAULT_ROLE_GRANTS
    write_roles: Mapping[str, Iterable[str]] = DEFAULT_WRITE_ROLES
    approver_roles: Mapping[str, Iterable[str]] = DEFAULT_APPROVER_ROLES
    # Add your custom sensitive fields here, e.g.
    # {**SENSITIVE_GROUPS, "price": PRICE_FIELDS | {"special_quote_price"}}.
    sensitive_groups: Mapping[str, Iterable[str]] = SENSITIVE_GROUPS

    # ─── Approval & audit hooks ─────────────────────────────

    @abstractmethod
    def verify_approval(
        self, token: str | None, action_hash: str
    ) -> ApprovalDecision:
        """Verify an approval token against the hash of the action.

        MUST be called (via ``authorize_write``) before ANY write. The token
        is issued by an approval service outside the ERP in the canonical
        format of ``issue_approval_token``. No production issuer exists yet
        (the chat gateway's execute path is deferred); the simplest
        conforming implementation is ``verify_approval_token(secret, token,
        action_hash, now=...)``. A conforming check:

        - the signature/MAC is valid (constant-time comparison);
        - it is bound to exactly this ``action_hash`` (no token reuse for a
          different action, which prevents TOCTOU swaps);
        - it has not expired;
        - it names an approver (``approver_id``), the approver's role
          (``approver_role``) and a unique ``approval_id``.

        Must never raise for a bad token; return ``ApprovalDecision(False,
        reason=...)`` instead. Anything not verifiable is a refusal.
        """

    def record_audit(self, event: dict[str, Any]) -> None:
        """Persist one audit event. Called for every tool call, allowed or
        refused.

        Default: one JSON line on ``sys.stderr`` (never silently dropped;
        stderr is safe next to an MCP stdio server, whose stdout is the
        protocol). Override to write to your append-only audit store.
        """
        sys.stderr.write(canonical_json(event) + "\n")
        sys.stderr.flush()

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
        return masked_field_names(ctx.role, self.role_grants, self.sensitive_groups)

    def authorize_write(
        self, ctx: CallContext, tool: str, args: Mapping[str, Any]
    ) -> tuple[ApprovalDecision, str]:
        """Gate for every write tool. Returns (decision, action_hash).

        Order: role allowed for this tool -> token present -> verify_approval
        -> token names an approval_id -> approver differs from requester
        (dual control) -> approver's role may approve this tool. Call this
        first in every write; if ``decision.valid`` is False, return a
        refused ``WriteResult`` and do not touch the ERP.

        This check is stateless. The write path must also enforce single
        use: after the idempotency lookup (same key -> replay), refuse with
        ``REASON_APPROVAL_ALREADY_USED`` if ``decision.approval_id`` already
        committed a write under another key, and record the approval_id as
        consumed in the same persistent record as the idempotency key.

        Raises CanonicalArgsError if ``args`` has no wire form (e.g. float).
        """
        action_hash = compute_action_hash(tool, args)
        allowed = set(self.write_roles.get(tool, ()))
        if ctx.role not in allowed:
            return ApprovalDecision(False, reason=REASON_ROLE_NOT_PERMITTED), action_hash
        if not ctx.approval_token:
            return ApprovalDecision(False, reason=REASON_APPROVAL_REQUIRED), action_hash
        decision = self.verify_approval(ctx.approval_token, action_hash)
        if not decision.valid:
            reason = decision.reason or "approval_invalid"
            return ApprovalDecision(False, reason=reason), action_hash
        if not decision.approval_id:
            return ApprovalDecision(False, reason=REASON_APPROVAL_MALFORMED), action_hash
        if not decision.approver_id or decision.approver_id == ctx.operator_id:
            return ApprovalDecision(False, reason=REASON_SELF_APPROVAL), action_hash
        if decision.approver_role not in set(self.approver_roles.get(tool, ())):
            return (
                ApprovalDecision(False, reason=REASON_APPROVER_ROLE_NOT_PERMITTED),
                action_hash,
            )
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
            approver_role=decision.approver_role,
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
    # verify_approval) -> idempotency lookup (same key: replay or conflict)
    # -> approval single-use check (approval_already_used) -> ERP write
    # through the ERP's official API / document interface (never direct
    # table INSERTs) -> mark key + approval_id done -> make_write_result.
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
