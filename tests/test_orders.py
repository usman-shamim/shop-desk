"""FR-5 / SC-003: the order total is recomputed in code and a planted mismatch is reported.

The model's stated total is never trusted: `recompute_total` derives the total from the line
items and `compare_total` reports a disagreement instead of silently accepting it.
"""

from __future__ import annotations

from shopdesk.orders import (
    LineItem,
    Order,
    compare_total,
    new_order_id,
    recompute_total,
)


def _order(*items: LineItem, total: float = 0.0) -> Order:
    return Order(order_id=new_order_id(), items=list(items), total=total)


def test_recompute_total_sums_qty_times_unit_price() -> None:
    order = _order(
        LineItem(sku="KTL-01", qty=3, unit_price=4200.0),
        LineItem(sku="IRN-07", qty=2, unit_price=3350.0),
    )
    assert recompute_total(order) == 3 * 4200.0 + 2 * 3350.0


def test_matching_total_is_accepted() -> None:
    order = _order(LineItem(sku="KTL-01", qty=4, unit_price=4200.0), total=16800.0)
    matches, recomputed = compare_total(order)
    assert matches is True
    assert recomputed == 16800.0


def test_planted_total_mismatch_is_detected() -> None:
    order = _order(LineItem(sku="KTL-01", qty=3, unit_price=4200.0), total=100.0)
    matches, recomputed = compare_total(order)
    assert matches is False
    assert recomputed == 12600.0


def test_empty_order_totals_zero() -> None:
    order = _order()
    assert recompute_total(order) == 0.0
    matches, recomputed = compare_total(order)
    assert recomputed == 0.0
    assert matches is True
