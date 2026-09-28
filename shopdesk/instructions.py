"""Dynamic instructions built per turn from context and the clock (FR-4).

The resolved prompt is a pure function of the shop context and the current (possibly simulated)
hour, so the same question at two different hours produces two different promises — and the
resolved text can be printed before any model call. The customer identifier is never written
into prompt text (FR-2).
"""

from __future__ import annotations

from typing import Any

from shopdesk.config import Settings, load_settings
from shopdesk.context import ShopContext

BASE = (
    "You are the Shop Desk for {shop}, answering customers in {currency}. "
    "Never state a price, stock figure or SKU that a tool did not give you in this conversation; "
    "if no tool supplied a figure, say you cannot confirm it. "
    "Use the price lookup tool for any price or stock question. "
    "When the customer confirms an order, hand the conversation to the order assembler. "
    "When the request is outside the catalogue, the item is unavailable, or the customer asks "
    "for a person, hand the conversation to a colleague with a typed reason."
)

OPEN_HOURS = "The shop is open until {close}:00, so same-day collection is possible."
CLOSED_HOURS = (
    "The shop is closed right now and opens at {open}:00. Do not promise same-day collection or "
    "delivery; tell the customer when the shop opens."
)

_settings: Settings | None = None


def set_settings(settings: Settings) -> None:
    """Inject the run's settings so the instruction callable needs no environment lookup."""
    global _settings
    _settings = settings


def get_settings() -> Settings:
    """The settings the Desk was started with, loaded lazily when not injected."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def build_instructions_text(context: ShopContext, settings: Settings) -> str:
    """Resolve the system instructions for this turn from context and the clock (FR-4)."""
    hour = settings.current_hour()
    if settings.is_open_at(hour):
        hours = OPEN_HOURS.format(close=settings.close_hour)
    else:
        hours = CLOSED_HOURS.format(open=settings.open_hour)
    return " ".join(
        (
            BASE.format(shop=context.shop, currency=context.currency),
            hours,
        )
    )


def build_instructions(run_context: Any, agent: Any) -> str:
    """The SDK instruction callable: ``(run_context, agent) -> str`` (FR-4)."""
    context = getattr(run_context, "context", None)
    if not isinstance(context, ShopContext):
        return BASE.format(shop="the shop", currency="the local currency")
    return build_instructions_text(context, get_settings())


def resolve_prompt(context: ShopContext, settings: Settings | None = None) -> str:
    """The prompt that would be sent this turn — printable before any model call (FR-4)."""
    return build_instructions_text(context, settings or get_settings())
