"""FR-3, FR-5, NFR-4: tool implementations answer from the catalogue and never raise.

Each implementation is called through the run-context shim the SDK supplies (`.context` is the
`ShopContext`), so the tests exercise the plain functions without a model or a network call.
Bad data (unknown SKU, quantity beyond stock, empty basket) must become a sentence, never an
exception, because a tool that raises is a defect (NFR-4).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shopdesk import messages, tools
from shopdesk.catalogue import load_catalogue
from shopdesk.context import ShopContext
from shopdesk.orders import LineItem

CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "catalogue.json"


@pytest.fixture()
def ctx() -> ShopContext:
    tools.set_catalogue(load_catalogue(CATALOGUE_PATH))
    return ShopContext(
        shop="Al-Noor Electronics",
        currency="PKR",
        customer_id="cust-1",
        tier="walk_in",
    )


def _shim(ctx: ShopContext) -> SimpleNamespace:
    return SimpleNamespace(context=ctx)


def test_lookup_price_returns_catalogue_price_and_names_sku(ctx: ShopContext) -> None:
    result = tools.lookup_price_impl(_shim(ctx), "KTL-01")
    assert "KTL-01" in result
    assert "4200" in result


def test_lookup_price_unknown_sku_returns_sentence(ctx: ShopContext) -> None:
    result = tools.lookup_price_impl(_shim(ctx), "NOPE-99")
    assert result == messages.NOT_IN_CATALOGUE
    assert isinstance(result, str)
    assert result.strip()


def test_lookup_price_never_raises_on_bad_input(ctx: ShopContext) -> None:
    for bad in ("", None, "  ", "not-a-sku"):
        result = tools.lookup_price_impl(_shim(ctx), bad)  # type: ignore[arg-type]
        assert isinstance(result, str)
        assert result.strip()


def test_zero_stock_returns_out_of_stock_sentence(ctx: ShopContext) -> None:
    result = tools.lookup_stock_impl(_shim(ctx), "FAN-22")
    assert messages.OUT_OF_STOCK in result


def test_add_to_basket_refuses_quantity_beyond_stock(ctx: ShopContext) -> None:
    result = tools.add_to_basket_impl(_shim(ctx), "KTL-01", 99)
    assert "We only have" in result
    assert "12" in result
    assert ctx.basket == []


def test_successful_add_updates_the_basket(ctx: ShopContext) -> None:
    result = tools.add_to_basket_impl(_shim(ctx), "KTL-01", 2)
    assert "KTL-01" in result
    assert len(ctx.basket) == 1
    line = ctx.basket[0]
    assert line.sku == "KTL-01"
    assert line.qty == 2
    assert line.unit_price == 4200.0


def test_confirm_order_empty_basket_returns_a_sentence(ctx: ShopContext) -> None:
    result = tools.confirm_order_impl(_shim(ctx))
    assert isinstance(result, str)
    assert result.strip()


def test_confirm_order_filled_basket_mentions_recomputed_total(ctx: ShopContext) -> None:
    ctx.basket = [LineItem(sku="KTL-01", qty=3, unit_price=4200.0)]
    result = tools.confirm_order_impl(_shim(ctx))
    assert "12600" in result.replace(",", "")
