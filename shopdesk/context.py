"""The shop context: typed, per-run, and never written into prompt text (FR-2).

Tools read this through the SDK's run-context wrapper, so no context parameter ever appears
in a tool's generated schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from shopdesk.orders import LineItem

Tier = Literal["walk_in", "regular"]
TIERS: tuple[str, ...] = ("walk_in", "regular")


@dataclass
class ShopContext:
    """Everything the Desk knows about the current run. FR-2: never in prompt text."""

    shop: str
    currency: str
    customer_id: str
    tier: Tier = "walk_in"
    session_id: str = "local"
    basket: list[LineItem] = field(default_factory=list)
    turns: int = 0
    escalated: bool = False

    def add_line(self, line: LineItem) -> None:
        """Merge a line into the basket, summing quantities for the same SKU (FR-5, FR-12)."""
        for existing in self.basket:
            if existing.sku == line.sku:
                existing.qty += line.qty
                return
        self.basket.append(line)

    def basket_total(self) -> float:
        return round(sum(line.qty * line.unit_price for line in self.basket), 2)

    def clear_basket(self) -> None:
        self.basket.clear()
