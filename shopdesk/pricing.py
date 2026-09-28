"""Pricing specialist as a tool (FR-8) and the run-level model override (FR-1 level 3).

FR-8: ``build_pricing_tool`` exposes the pricing agent with ``as_tool`` and a
``custom_output_extractor`` that returns only the figure, so the Desk re-words it and the
specialist's prose never reaches the customer. ``PRICING_INSTRUCTIONS`` forbids prose.

FR-1 level 3: ``re_quote`` runs a nested ``Runner.run`` whose ``RunConfig`` carries
``model="gpt-5-mini"`` for that single run only. The nested agent is constructed inside the
function (importing ``shopdesk.agents`` here would be circular), and any failure is returned
as ``messages.TOOL_FAILURE`` rather than raised (NFR-4).
"""

from __future__ import annotations

import asyncio
import re
import threading
from collections.abc import Coroutine
from typing import Any

from agents import Agent, FunctionTool, RunContextWrapper, Runner, RunConfig, function_tool
from agents.result import RunResult, RunResultStreaming

from shopdesk import messages
from shopdesk.catalogue import Catalogue, Product, load_catalogue
from shopdesk.config import load_settings
from shopdesk.context import ShopContext

PRICING_TOOL_NAME = "pricing_specialist"

PRICING_INSTRUCTIONS = (
    "You are the pricing specialist. State the price of the item under discussion as a bare "
    "figure: a number, optionally followed by its currency code (for example 4200 PKR). "
    "Output nothing else - no prose, no currency words beyond the code, and no explanation."
)

_FIGURE_RE = re.compile(r"\d+(?:[.,]\d+)?")

_catalogue: Catalogue | None = None


def set_catalogue(catalogue: Catalogue | None) -> None:
    """Inject the catalogue this module should price against (NFR-3)."""
    global _catalogue
    _catalogue = catalogue


def get_catalogue() -> Catalogue:
    """Return the injected catalogue, lazily loading it from config on first use (NFR-3)."""
    global _catalogue
    if _catalogue is None:
        _catalogue = load_catalogue(load_settings().catalogue_path)
    return _catalogue


def _content_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    texts: list[str] = []
    content = getattr(value, "content", None)
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for part in content:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str):
                texts.append(part_text)
    text = getattr(value, "text", None)
    if isinstance(text, str):
        texts.append(text)
    return texts


def _result_texts(run_result: Any) -> list[str]:
    texts: list[str] = []
    for item in getattr(run_result, "new_items", None) or []:
        texts.extend(_content_texts(getattr(item, "raw_item", item)))
        output = getattr(item, "output", None)
        if output is not None:
            texts.extend(_content_texts(output))
    return texts


def _last_figure(run_result: Any) -> str | None:
    figures: list[str] = []
    for text in _result_texts(run_result):
        figures.extend(_FIGURE_RE.findall(text))
    return figures[-1] if figures else None


def _figure_from_result(run_result: Any) -> str:
    figure = _last_figure(run_result)
    if figure is not None:
        return figure
    final = str(getattr(run_result, "final_output", "")).strip()
    matches = _FIGURE_RE.findall(final)
    return matches[-1] if matches else final


async def extract_figure(run_result: RunResult | RunResultStreaming) -> str:
    """Return only the figure from the specialist's nested run (FR-8)."""
    return _figure_from_result(run_result)


def build_pricing_tool(pricing_agent: Agent[Any]) -> FunctionTool:
    """Expose the pricing specialist as a figure-only tool (FR-8)."""
    return pricing_agent.as_tool(
        tool_name=PRICING_TOOL_NAME,
        tool_description="Get a definitive price figure for a catalogue item, as a number.",
        custom_output_extractor=extract_figure,
    )


def _drive(coro: Coroutine[Any, Any, Any]) -> Any:
    """Await a coroutine from synchronous code, even inside a running event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    box: list[Any] = []
    failure: list[Exception] = []

    def _target() -> None:
        try:
            box.append(asyncio.run(coro))
        except Exception as exc:
            failure.append(exc)

    worker = threading.Thread(target=_target, daemon=True)
    worker.start()
    worker.join()
    if failure:
        raise failure[0]
    return box[0]


def _re_quote_prompt(product: Product, currency: str) -> str:
    return (
        f"SKU {product.sku}: {product.name}, catalogue price {product.price} {currency}. "
        "Reply with the price figure only."
    )


def re_quote_impl(context: RunContextWrapper[ShopContext], sku: str) -> str:
    """Re-quote a catalogue SKU through a single run-level override (FR-1 level 3)."""
    catalogue = get_catalogue()
    product = catalogue.find(sku)
    if product is None:
        return messages.NOT_IN_CATALOGUE

    agent = Agent(name="re_quote_specialist", instructions=PRICING_INSTRUCTIONS)
    prompt = _re_quote_prompt(product, catalogue.currency)
    try:
        result = _drive(
            Runner.run(agent, prompt, run_config=RunConfig(model="gpt-5-mini"))
        )
    except Exception:
        return messages.TOOL_FAILURE

    figure = _figure_from_result(result).strip()
    if not figure:
        return messages.TOOL_FAILURE
    return f"{product.name} is {figure} {catalogue.currency}."


def _shop_style_error(context: RunContextWrapper[ShopContext], error: Exception) -> str:
    return messages.TOOL_FAILURE


re_quote: FunctionTool = function_tool(
    re_quote_impl,
    name_override="re_quote",
    description_override="Re-quote a catalogue price through the stronger model for one run.",
    failure_error_function=_shop_style_error,
)
