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

This is NOT a runnable server. It's the contract.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class CustomerMaster:
    id: str
    name: str
    grade: str  # "A" | "B" | "C"
    credit_limit: Decimal
    credit_used: Decimal
    payment_terms: str  # e.g. "T/T 30", "Net 60"
    industry: str | None = None
    requires_iatf: bool = False  # 汽車業客戶通常 True


@dataclass
class PartMaster:
    part_no: str
    name: str
    spec: str
    standard_cost: Decimal
    unit: str  # "PCS" | "KG" | "M"
    abc_class: str  # "A" | "B" | "C"


@dataclass
class InventorySnapshot:
    part_no: str
    on_hand: int | float
    in_transit: int | float
    safety_stock: int | float
    abc_class: str
    last_movement_at: datetime


@dataclass
class MachineRate:
    machine: str
    hourly_rate: Decimal  # 含人工 + 折舊 + 管理 + 水電
    setup_rate: Decimal
    valid_from: datetime
    valid_to: datetime | None = None


class ErpConnector(ABC):
    """Implement this for your ERP."""

    # ─── Read tools ─────────────────────────────────────────

    @abstractmethod
    def get_customer(self, customer_id: str) -> CustomerMaster | None:
        ...

    @abstractmethod
    def get_part_master(self, part_no: str) -> PartMaster | None:
        ...

    @abstractmethod
    def get_inventory(self, part_no: str) -> InventorySnapshot | None:
        ...

    @abstractmethod
    def get_recent_purchase_price(
        self, part_no: str, days: int = 30
    ) -> Decimal | None:
        """Returns latest purchase unit price within N days, or None."""

    @abstractmethod
    def get_machine_rate(self, machine: str) -> MachineRate | None:
        ...

    @abstractmethod
    def get_credit_status(self, customer_id: str) -> dict:
        """Returns: {credit_limit, credit_used, available, warnings}"""

    # ─── Write tools (high-impact, must audit) ──────────────

    @abstractmethod
    def create_sales_order(
        self,
        customer_id: str,
        items: list[dict],
        delivery_date: datetime,
        po_reference: str,
        operator: str,  # who triggered (audit)
    ) -> str:
        """Returns SO ID."""

    @abstractmethod
    def create_purchase_request(
        self,
        items: list[dict],
        urgency: str,
        operator: str,
    ) -> str:
        """Returns PR ID."""

    @abstractmethod
    def update_inventory_movement(
        self,
        part_no: str,
        qty: float,
        direction: str,  # "in" | "out"
        reference: str,  # e.g. WO ID
        operator: str,
    ) -> bool:
        ...

    @abstractmethod
    def close_sales_order(
        self, so_id: str, shipment_doc: dict, operator: str
    ) -> bool:
        ...
