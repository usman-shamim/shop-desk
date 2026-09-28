"""FR-2, FR-7, SC-004: tool visibility — no context in the schema, and the tool set by tier.

The seasonal tool is switched off statically so it appears in no interface, the loyalty tool is
offered to regular customers only, and the price lookup's generated schema never exposes the
run context (the decorator drops the first, `RunContextWrapper`-typed parameter).
"""

from __future__ import annotations

import asyncio
import inspect
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("agents")

from shopdesk import tools
from shopdesk.context import ShopContext


def _shim(ctx: ShopContext) -> SimpleNamespace:
    return SimpleNamespace(context=ctx)


def _context(tier: str) -> ShopContext:
    return ShopContext(
        shop="Al-Noor Electronics",
        currency="PKR",
        customer_id="cust-1",
        tier=tier,  # type: ignore[arg-type]
    )


def _resolve(value: Any) -> Any:
    if inspect.isawaitable(value):
        return asyncio.run(value)
    return value


def _enabled_names(tier: str) -> list[str]:
    shim = _shim(_context(tier))
    names: list[str] = []
    for tool in tools.DESK_TOOLS:
        enabled = tool.is_enabled
        if callable(enabled):
            enabled = _resolve(enabled(shim, None))
        if enabled:
            names.append(tool.name)
    return names


def test_seasonal_tool_enabled_state_is_falsy() -> None:
    assert not tools.seasonal_offer.is_enabled


def test_loyalty_tool_is_enabled_only_for_regular_tier() -> None:
    is_enabled = tools.loyalty_quote.is_enabled
    assert callable(is_enabled)
    walk_in = _resolve(is_enabled(_shim(_context("walk_in")), None))
    regular = _resolve(is_enabled(_shim(_context("regular")), None))
    assert walk_in is False
    assert regular is True


def test_price_lookup_schema_exposes_no_context_parameter() -> None:
    schema = getattr(tools.lookup_price, "params_json_schema", None)
    if schema is None:
        params = list(inspect.signature(tools.lookup_price_impl).parameters)
        assert params[0] in {"context", "ctx"}
        assert "sku" in params
        return
    properties = schema.get("properties", {})
    assert "sku" in properties
    assert "context" not in properties
    assert "ctx" not in properties


def test_tier_tool_sets_differ_and_seasonal_is_in_neither() -> None:
    walk_in = _enabled_names("walk_in")
    regular = _enabled_names("regular")
    assert "seasonal_offer" not in walk_in
    assert "seasonal_offer" not in regular
    assert "loyalty_quote" not in walk_in
    assert "loyalty_quote" in regular
    assert walk_in != regular
