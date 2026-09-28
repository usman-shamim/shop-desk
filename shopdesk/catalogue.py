"""Catalogue access — the only permitted source of price, stock and SKU truth (NFR-3).

The file is read once per run and every lookup goes through here, so the output guardrail can
compare an answer against exactly the data the run used (FR-6).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CATALOGUE_MISSING_SENTENCE = "Shop Desk cannot start: the catalogue file {path} was not found."
CATALOGUE_MALFORMED_SENTENCE = "Shop Desk cannot start: the catalogue file {path} is not valid JSON."
CATALOGUE_INCOMPLETE_SENTENCE = "Shop Desk cannot start: the catalogue file {path} is missing required product fields."


class CatalogueError(RuntimeError):
    """A startup problem with the catalogue file. Always one readable sentence (NFR-4)."""


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price: float
    stock: int


@dataclass(frozen=True)
class Catalogue:
    shop: str
    currency: str
    products: tuple[Product, ...]

    def find(self, sku: str) -> Product | None:
        wanted = (sku or "").strip().upper()
        for product in self.products:
            if product.sku.upper() == wanted:
                return product
        return None

    def skus(self) -> set[str]:
        return {product.sku.upper() for product in self.products}

    def prices(self) -> set[float]:
        return {round(product.price, 2) for product in self.products}


def load_catalogue(path: Path) -> Catalogue:
    """Load and validate the catalogue. Raises CatalogueError with one sentence (NFR-4)."""
    path = Path(path)
    if not path.exists():
        raise CatalogueError(CATALOGUE_MISSING_SENTENCE.format(path=path))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CatalogueError(CATALOGUE_MALFORMED_SENTENCE.format(path=path)) from exc

    try:
        products = tuple(
            Product(
                sku=str(item["sku"]),
                name=str(item["name"]),
                price=float(item["price"]),
                stock=int(item["stock"]),
            )
            for item in raw["products"]
        )
        catalogue = Catalogue(
            shop=str(raw["shop"]), currency=str(raw["currency"]), products=products
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CatalogueError(CATALOGUE_INCOMPLETE_SENTENCE.format(path=path)) from exc

    return catalogue


def find(catalogue: Catalogue, sku: str) -> Product | None:
    return catalogue.find(sku)


def all_products(catalogue: Catalogue) -> tuple[Product, ...]:
    return catalogue.products
