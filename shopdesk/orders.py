"""Typed order structures and the only legitimate source of a total (FR-5).

The model's stated total is never trusted: `recompute_total` derives it from the line items
and `compare_total` reports a mismatch instead of silently accepting it.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

OrderStatus = Literal["draft", "confirmed", "escalated"]


class LineItem(BaseModel):
    sku: str
    qty: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class Order(BaseModel):
    order_id: str
    status: OrderStatus = "draft"
    items: list[LineItem] = Field(default_factory=list)
    total: float = 0.0


def new_order_id() -> str:
    """Generated in Python, never by the model (FR-5)."""
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def recompute_total(order: Order) -> float:
    """The only total the Desk may state (FR-5)."""
    return round(sum(item.qty * item.unit_price for item in order.items), 2)


def compare_total(order: Order) -> tuple[bool, float]:
    """Return (matches, recomputed). A False means the mismatch must be reported (FR-5)."""
    recomputed = recompute_total(order)
    return abs(round(order.total, 2) - recomputed) < 0.01, recomputed
