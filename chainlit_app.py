"""Chainlit browser entry point for Shop Desk.

Serves FR-12: every browser window gets its own ShopContext and ShopDeskRunner so two
sessions never share a basket, history is trimmed past six exchanges (tool-call items first),
and configuration or catalogue failures surface as one readable sentence instead of a stack
trace (NFR-1, NFR-4).
"""

from __future__ import annotations

import uuid

import chainlit as cl

from shopdesk.catalogue import Catalogue, CatalogueError, load_catalogue
from shopdesk.config import ConfigError, Settings, load_settings
from shopdesk.context import ShopContext
from shopdesk.runner import ShopDeskRunner

WELCOME = "Welcome to {shop}. Prices are shown in {currency}. Ask about an item, or type /cost or /history."
UNAVAILABLE = "Shop Desk is not available right now — check the configuration and reload."


def start_session() -> ShopDeskRunner:
    """Load config and catalogue and bind a fresh runner to this browser session (FR-12)."""
    settings: Settings = load_settings()
    catalogue: Catalogue = load_catalogue(settings.catalogue_path)
    session_id = uuid.uuid4().hex
    context = ShopContext(
        shop=catalogue.shop,
        currency=catalogue.currency,
        customer_id=session_id,
        session_id=session_id,
    )
    runner = ShopDeskRunner(settings, catalogue, context)
    cl.user_session.set("runner", runner)
    cl.user_session.set("context", context)
    cl.user_session.set("trimmed", 0)
    cl.user_session.set("shop", catalogue.shop)
    cl.user_session.set("currency", catalogue.currency)
    return runner


@cl.on_chat_start
async def on_chat_start() -> None:
    try:
        start_session()
    except (ConfigError, CatalogueError) as exc:
        await cl.Message(content=str(exc)).send()
        return
    shop = cl.user_session.get("shop")
    currency = cl.user_session.get("currency")
    await cl.Message(content=WELCOME.format(shop=shop, currency=currency)).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    runner: ShopDeskRunner | None = cl.user_session.get("runner")
    if runner is None:
        await cl.Message(content=UNAVAILABLE).send()
        return

    text = (message.content or "").strip()
    if text == "/cost":
        await cl.Message(content=runner.cost_line()).send()
        return
    if text == "/history":
        await cl.Message(content=_history_summary(runner)).send()
        return

    reply = await runner.run_turn(text)
    await cl.Message(content=reply).send()
    _trim(runner)


def _trim(runner: ShopDeskRunner) -> None:
    """Apply the FR-12 trim rule via the runner and remember how many items it dropped."""
    before = list(runner.history)
    trimmed = runner.trim_history(before)
    dropped = len(before) - len(trimmed)
    if dropped > 0:
        cl.user_session.set("trimmed", (cl.user_session.get("trimmed") or 0) + dropped)
    runner.history = trimmed


def _history_summary(runner: ShopDeskRunner) -> str:
    carried = len(runner.history)
    trimmed = cl.user_session.get("trimmed") or 0
    return f"Carrying {carried} history items; {trimmed} trimmed so far."
