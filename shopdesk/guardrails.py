"""Output guardrail: an answer may only quote prices and SKUs from the catalogue (FR-6, SC-002).

The finished answer is scanned for price-shaped and SKU-shaped tokens, and each one is looked
up in the catalogue loaded for the run. This is a set comparison against the file, not a
judgement, so editing a catalogue price makes a previously passing answer trip.

Nothing here runs at import time: the catalogue is loaded lazily, on first use, so the module
imports and can be exercised without an API key.
"""

from __future__ import annotations

import re
from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    OutputGuardrail,
    RunContextWrapper,
    output_guardrail,
)

from shopdesk.catalogue import Catalogue, load_catalogue
from shopdesk.config import load_settings
from shopdesk.context import ShopContext
from shopdesk.orders import recompute_total

GUARDRAIL_NAME = "catalogue_truth_guardrail"

_CATALOGUE: Catalogue | None = None


def set_catalogue(catalogue: Catalogue | None) -> None:
    """Inject the catalogue loaded for the current run (None clears it for a lazy reload)."""
    global _CATALOGUE
    _CATALOGUE = catalogue


def get_catalogue() -> Catalogue:
    """Return the run's catalogue, loading it from settings on first use."""
    global _CATALOGUE
    if _CATALOGUE is None:
        _CATALOGUE = load_catalogue(load_settings().catalogue_path)
    return _CATALOGUE


# A price-shaped token: an integer with optional thousands separators and optional decimals.
# The leading lookbehind keeps a number glued to letters or a hyphen (a SKU suffix like "-01")
# out of the match; the trailing unit group captures a single letter so identifiers such as
# "1200W" or "1.7L" are recognised as measurements and dropped rather than read as prices.
_PRICE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9-])"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)"
    r"(?P<unit>[A-Za-z]?)"
)

_SKU_PATTERN = re.compile(r"\b[A-Za-z]{3}-\d{2}\b")


def extract_price_tokens(text: str) -> list[float]:
    """Return the rounded floats for every price-shaped token in ``text`` (FR-6)."""
    tokens: list[float] = []
    for match in _PRICE_PATTERN.finditer(text or ""):
        if match.group("unit"):
            continue
        raw = match.group("number").rstrip(",")
        if not raw:
            continue
        tokens.append(round(float(raw.replace(",", "")), 2))
    return tokens


def extract_sku_tokens(text: str) -> list[str]:
    """Return every SKU-shaped token in ``text``, upper-cased (FR-6)."""
    return [match.group(0).upper() for match in _SKU_PATTERN.finditer(text or "")]


def check_answer(
    text: str,
    catalogue: Catalogue | None = None,
    extra_allowed: list[float] | None = None,
) -> tuple[bool, list[float | str]]:
    """Check a finished answer against the catalogue.

    Returns ``(ok, offending)``: ``offending`` holds every price token whose value (rounded to
    two decimals) is not a catalogue price, and every SKU token that is not a catalogue SKU.
    ``ok`` is True when nothing is offending.

    Two refinements keep this a data check rather than a trap for honest answers: a figure below
    the cheapest catalogue price cannot be a catalogue price, so it is read as a quantity or a
    stock count; and ``extra_allowed`` carries figures the run computed from the catalogue itself
    (a basket total, a recomputed order total), which are legitimately not catalogue rows.
    """
    catalogue = catalogue if catalogue is not None else get_catalogue()
    prices = catalogue.prices()
    skus = catalogue.skus()
    floor = min(prices) if prices else 0.0
    allowed = prices | {round(float(value), 2) for value in (extra_allowed or [])}

    offending: list[float | str] = []
    seen: set[float | str] = set()

    for token in extract_price_tokens(text):
        if token < floor:
            continue
        if round(token, 2) not in allowed and token not in seen:
            seen.add(token)
            offending.append(token)

    for token in extract_sku_tokens(text):
        if token not in skus and token not in seen:
            seen.add(token)
            offending.append(token)

    return (not offending, offending)


def _answer_text(output: Any) -> str:
    """Coerce an agent output to text without raising on unusual types."""
    if isinstance(output, str):
        return output
    if output is None:
        return ""
    try:
        return str(output)
    except Exception:
        return ""


def _allowed_from_context(ctx: Any) -> list[float]:
    """Figures this run computed from the catalogue: the basket total and recomputed totals."""
    shop_context = getattr(ctx, "context", None)
    if not isinstance(shop_context, ShopContext):
        return []
    allowed = [round(float(shop_context.basket_total()), 2)]
    for order in getattr(shop_context, "orders", None) or []:
        try:
            allowed.append(round(float(recompute_total(order)), 2))
        except Exception:
            continue
    return allowed


@output_guardrail
async def catalogue_truth_guardrail(
    ctx: RunContextWrapper[ShopContext], agent: Agent[Any], output: Any
) -> GuardrailFunctionOutput:
    """Trip when the finished answer quotes a price or SKU absent from the catalogue (FR-6)."""
    text = _answer_text(output)
    if not text.strip():
        return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)

    ok, offending = check_answer(text, extra_allowed=_allowed_from_context(ctx))
    if ok:
        return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)

    return GuardrailFunctionOutput(
        output_info={"reason": "price_or_sku_not_in_catalogue", "offending": offending},
        tripwire_triggered=True,
    )


OUTPUT_GUARDRAILS: list[OutputGuardrail[ShopContext]] = [catalogue_truth_guardrail]
