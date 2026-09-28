"""FR-6 / SC-002: the output guardrail compares an answer against the catalogue file.

A price or SKU the answer quotes must exist in the catalogue loaded for the run, so editing a
catalogue price makes a previously passing answer trip. This is a comparison against the file,
not a judgement, and unit-style tokens ("1.7L", "1200W") are measurements, not prices.
"""

from __future__ import annotations

import json
from pathlib import Path

from shopdesk.catalogue import Catalogue, load_catalogue
from shopdesk.guardrails import check_answer, extract_price_tokens, extract_sku_tokens

CATALOGUE_PATH = Path(__file__).resolve().parents[1] / "catalogue.json"

# A catalogue-true answer: the SKU exists and the only price-shaped token is the catalogue price.
TRUE_ANSWER = "SKU KTL-01 — Electric kettle 1.7L costs 4200 PKR."


def _catalogue() -> Catalogue:
    return load_catalogue(CATALOGUE_PATH)


def test_catalogue_true_answer_passes() -> None:
    ok, offending = check_answer(TRUE_ANSWER, _catalogue())
    assert ok is True
    assert offending == []


def test_stranger_price_fails_and_is_reported() -> None:
    ok, offending = check_answer("The kettle costs 9999 PKR.", _catalogue())
    assert ok is False
    assert any(float(token) == 9999.0 for token in offending if not isinstance(token, str))


def test_stranger_sku_fails_and_is_reported() -> None:
    ok, offending = check_answer("SKU ZZZ-99 costs 4200 PKR.", _catalogue())
    assert ok is False
    assert "ZZZ-99" in offending


def test_editing_the_catalogue_makes_a_passing_answer_fail(tmp_path: Path) -> None:
    original = _catalogue()
    ok_before, offending_before = check_answer(TRUE_ANSWER, original)
    assert ok_before is True, offending_before

    data = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    for product in data["products"]:
        if product["sku"] == "KTL-01":
            product["price"] = 4321
    edited_path = tmp_path / "catalogue.json"
    edited_path.write_text(json.dumps(data), encoding="utf-8")

    ok_after, offending_after = check_answer(TRUE_ANSWER, load_catalogue(edited_path))
    assert ok_after is False
    assert any(float(token) == 4200.0 for token in offending_after if not isinstance(token, str))


def test_unit_style_tokens_are_not_treated_as_prices() -> None:
    assert extract_price_tokens("Electric kettle 1.7L") == []
    assert extract_price_tokens("Steam iron 1200W") == []
    assert 1.7 not in extract_price_tokens("Electric kettle 1.7L")
    assert 1200.0 not in extract_price_tokens("Steam iron 1200W")


def test_a_real_price_is_still_extracted() -> None:
    assert 4200.0 in extract_price_tokens("The kettle costs 4200 PKR.")
    assert extract_sku_tokens("SKU KTL-01 costs 4200 PKR.") == ["KTL-01"]
