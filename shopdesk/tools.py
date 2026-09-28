"""The Desk's function tools (FR-2, FR-3, FR-5, FR-7, NFR-3, NFR-4).

Each tool is a plain Python implementation function, so tests can call it without the SDK
runtime, plus a `FunctionTool` built from that function for the agents to use. Implementations
read the run's `ShopContext` through the run-context wrapper only (`context.context`), which
keeps the context out of every generated tool schema (FR-2). Price, stock and SKU always come
from the catalogue loaded for the run (NFR-3); bad data and unexpected errors become a sentence
instead of an exception (NFR-4).

`seasonal_offer` is constructed disabled so it appears in no tool interface at all, and
`loyalty_quote` is enabled by a callable that admits the regular tier only (FR-7).
"""

from __future__ import annotations

from typing import Any

from agents import FunctionTool, RunContextWrapper, function_tool

from shopdesk import messages
from shopdesk.catalogue import Catalogue, load_catalogue
from shopdesk.config import load_settings
from shopdesk.context import ShopContext
from shopdesk.orders import LineItem, Order, compare_total, new_order_id

LOYALTY_DISCOUNT_RATE = 0.10

_catalogue: Catalogue | None = None


def set_catalogue(catalogue: Catalogue) -> None:
    """Inject the catalogue loaded for this run (the runner calls this before a run)."""
    global _catalogue
    _catalogue = catalogue


def get_catalogue() -> Catalogue:
    """The catalogue for this run, loaded lazily from configuration when not injected."""
    global _catalogue
    if _catalogue is None:
        _catalogue = load_catalogue(load_settings().catalogue_path)
    return _catalogue


def shop_style_error(context: RunContextWrapper[ShopContext], error: Exception) -> str:
    """Return the Desk's voice for any tool failure instead of raising into the runner (NFR-4)."""
    return messages.TOOL_FAILURE


def lookup_price_impl(context: RunContextWrapper[ShopContext], sku: str) -> str:
    """Look up one item's catalogue price and stock by SKU."""
    try:
        catalogue = get_catalogue()
        product = catalogue.find(sku)
        if product is None:
            return messages.NOT_IN_CATALOGUE
        sentence = (
            f"SKU {product.sku} — {product.name} costs {product.price:g} "
            f"{catalogue.currency} ({product.stock} in stock)."
        )
        if product.stock <= 0:
            sentence = f"{sentence} {messages.OUT_OF_STOCK}"
        return sentence
    except Exception:
        return messages.TOOL_FAILURE


def lookup_stock_impl(context: RunContextWrapper[ShopContext], sku: str) -> str:
    """Say whether one item is available and how many the catalogue shows."""
    try:
        catalogue = get_catalogue()
        product = catalogue.find(sku)
        if product is None:
            return messages.NOT_IN_CATALOGUE
        if product.stock <= 0:
            return messages.OUT_OF_STOCK
        return (
            f"We have {product.stock} of {product.name} (SKU {product.sku}) in stock "
            f"right now, as read from the catalogue."
        )
    except Exception:
        return messages.TOOL_FAILURE


def add_to_basket_impl(context: RunContextWrapper[ShopContext], sku: str, qty: int) -> str:
    """Add a quantity of a catalogue item to the session basket."""
    try:
        shop_context = context.context
        if qty < 1:
            return "I can only add whole items — the quantity needs to be at least one."
        catalogue = get_catalogue()
        product = catalogue.find(sku)
        if product is None:
            return messages.NOT_IN_CATALOGUE
        if qty > product.stock:
            return messages.QUANTITY_BEYOND_STOCK.format(stock=product.stock, name=product.name)
        shop_context.add_line(LineItem(sku=product.sku, qty=qty, unit_price=product.price))
        total = shop_context.basket_total()
        return (
            f"Added {qty} × {product.name} (SKU {product.sku}) at {product.price:g} each — "
            f"your basket is now {total:g} {catalogue.currency}."
        )
    except Exception:
        return messages.TOOL_FAILURE


def confirm_order_impl(context: RunContextWrapper[ShopContext]) -> str:
    """Turn the session basket into a typed, confirmed order and report the recomputed total."""
    try:
        shop_context = context.context
        basket = list(shop_context.basket)
        if not basket:
            return "There's nothing in your basket to confirm yet — tell me what you'd like."

        order = Order(
            order_id=new_order_id(),
            status="confirmed",
            items=basket,
            total=shop_context.basket_total(),
        )
        matches, recomputed = compare_total(order)
        _store_order(shop_context, order)

        currency = shop_context.currency
        item_count = len(order.items)
        if not matches:
            return (
                f"Order {order.order_id} covers {item_count} items, but the stated total "
                f"{order.total:g} {currency} does not match the recomputed total "
                f"{recomputed:g} {currency}."
            )
        return (
            f"Order {order.order_id} is confirmed with {item_count} items — "
            f"the total is {recomputed:g} {currency}."
        )
    except Exception:
        return messages.TOOL_FAILURE


def loyalty_quote_impl(context: RunContextWrapper[ShopContext]) -> str:
    """Quote the loyalty price for the current basket to a regular customer."""
    try:
        shop_context = context.context
        if not shop_context.basket:
            return (
                "Loyalty pricing starts with your first item — tell me what you're after "
                "and I'll price it for you."
            )
        total = shop_context.basket_total()
        percent = round(LOYALTY_DISCOUNT_RATE * 100)
        return (
            f"As a regular customer, your basket of {total:g} {shop_context.currency} carries a "
            f"{percent}% loyalty discount that we apply at the counter. I won't quote the "
            "discounted figure because it isn't a catalogue price."
        )
    except Exception:
        return messages.TOOL_FAILURE


def seasonal_offer_impl(context: RunContextWrapper[ShopContext]) -> str:
    """Return the seasonal offer line. This tool is never enabled, so it cannot be called."""
    return (
        "We have a seasonal offer on selected items this week — ask me about the kettle "
        "or the steam iron."
    )


def _store_order(shop_context: Any, order: Order) -> None:
    orders = getattr(shop_context, "orders", None)
    if isinstance(orders, list):
        orders.append(order)
        return
    setattr(shop_context, "orders", [order])


def loyalty_enabled(*args: Any) -> bool:
    """Enable the loyalty tool for the regular tier only (FR-7). Version-robust by arity."""
    return args[0].context.tier == "regular"


lookup_price: FunctionTool = function_tool(
    name_override="lookup_price",
    failure_error_function=shop_style_error,
)(lookup_price_impl)

lookup_stock: FunctionTool = function_tool(
    name_override="lookup_stock",
    failure_error_function=shop_style_error,
)(lookup_stock_impl)

add_to_basket: FunctionTool = function_tool(
    name_override="add_to_basket",
    failure_error_function=shop_style_error,
)(add_to_basket_impl)

confirm_order: FunctionTool = function_tool(
    name_override="confirm_order",
    failure_error_function=shop_style_error,
)(confirm_order_impl)

loyalty_quote: FunctionTool = function_tool(
    name_override="loyalty_quote",
    failure_error_function=shop_style_error,
    is_enabled=loyalty_enabled,
)(loyalty_quote_impl)

seasonal_offer: FunctionTool = function_tool(
    name_override="seasonal_offer",
    failure_error_function=shop_style_error,
    is_enabled=False,
)(seasonal_offer_impl)

DESK_TOOLS: list[FunctionTool] = [
    lookup_price,
    lookup_stock,
    add_to_basket,
    confirm_order,
    loyalty_quote,
    seasonal_offer,
]
