"""The guardrail must refuse invention without refusing honest arithmetic (FR-6, SC-002)."""

from __future__ import annotations

import json
from pathlib import Path

from shopdesk.catalogue import load_catalogue
from shopdesk.context import ShopContext
from shopdesk.guardrails import check_answer
from shopdesk.orders import LineItem, Order, recompute_total

CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "catalogue.json"
CATALOGUE = load_catalogue(CATALOGUE_PATH)


def test_quantity_below_the_cheapest_price_is_not_treated_as_a_price() -> None:
    ok, offending = check_answer("I've added 3 electric kettles (KTL-01).", CATALOGUE)
    assert ok, offending


def test_basket_total_computed_from_the_catalogue_is_allowed() -> None:
    total = 3 * 4200.0
    ok, offending = check_answer(
        f"Three kettles come to {total:g} PKR.", CATALOGUE, extra_allowed=[total]
    )
    assert ok, offending


def test_recomputed_order_total_is_allowed_but_a_stranger_figure_is_not() -> None:
    order = Order(
        order_id="ORD-TEST",
        status="confirmed",
        items=[LineItem(sku="KTL-01", qty=3, unit_price=4200.0)],
        total=99999.0,
    )
    recomputed = recompute_total(order)
    ok, offending = check_answer(
        f"The order total is {recomputed:g} PKR.", CATALOGUE, extra_allowed=[recomputed]
    )
    assert ok, offending

    refused, offending = check_answer("It comes to 99999 PKR.", CATALOGUE, extra_allowed=[recomputed])
    assert not refused
    assert 99999.0 in offending


def test_results_survive_an_edited_catalogue(tmp_path: Path) -> None:
    source = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    for product in source["products"]:
        if product["sku"] == "KTL-01":
            product["price"] = 4500
    edited = tmp_path / "catalogue.json"
    edited.write_text(json.dumps(source), encoding="utf-8")
    edited_catalogue = load_catalogue(edited)

    ok_before, _ = check_answer("The kettle is 4200 PKR (KTL-01).", CATALOGUE)
    ok_after, offending = check_answer("The kettle is 4200 PKR (KTL-01).", edited_catalogue)

    assert ok_before
    assert not ok_after
    assert 4200.0 in offending


def test_guardrail_ignores_the_customer_identifier_and_units() -> None:
    context = ShopContext(shop="Al-Noor Electronics", currency="PKR", customer_id="cust-42")
    assert context.customer_id == "cust-42"
    ok, offending = check_answer(
        "The hand blender is 2600 PKR and the iron is 1200W.", CATALOGUE
    )
    assert ok, offending


def test_loyalty_answer_survives_the_guardrail_and_quotes_no_derived_price() -> None:
    """FR-6 x FR-7: a loyalty answer must not quote a figure the catalogue never had."""
    from types import SimpleNamespace

    from shopdesk.tools import loyalty_quote_impl, set_catalogue

    set_catalogue(CATALOGUE)
    context = ShopContext(shop="Al-Noor Electronics", currency="PKR", customer_id="cust-7")
    context.add_line(LineItem(sku="KTL-01", qty=3, unit_price=4200.0))
    answer = loyalty_quote_impl(SimpleNamespace(context=context))

    discounted = round(context.basket_total() * 0.9, 2)
    assert f"{discounted:g}" not in answer
    ok, offending = check_answer(answer, CATALOGUE, extra_allowed=[context.basket_total()])
    assert ok, offending
