# Contract: Tools

Every tool is a plain Python function decorated with the SDK's function-tool decorator, takes
`context: RunContextWrapper[ShopContext]` as its first parameter (excluded from the generated
schema — FR-2), and returns either a `str` or a pydantic model. Every tool sets
`failure_error_function` to `shop_style_error`, which returns a sentence (NFR-4). No tool
raises into the runner.

## lookup_price — the fast-path tool (FR-3)

```python
def lookup_price(context: RunContextWrapper[ShopContext], sku: str) -> str: ...
```

- **Input schema**: `{ "sku": string }` — no context parameter.
- **Returns**: `"SKU KTL-01 — Electric kettle 1.7L costs 4200 PKR (12 in stock)."` or
  `"I can't confirm a price for that item — it isn't in our catalogue."`
- **Fast-path contract**: when this tool is the one the Desk calls, the run ends with the tool
  output as the final answer — the model does not see the value and writes no sentence around
  it (`tool_use_behavior`, `fastpath.py`). Call count for such a turn: **1**.
- **Truth**: the price and stock come from the catalogue loaded for this run (NFR-3).

## lookup_stock (FR-3, FR-6)

```python
def lookup_stock(context: RunContextWrapper[ShopContext], sku: str) -> str: ...
```

- **Returns**: availability sentence, or the not-in-catalogue sentence, or
  `"...is out of stock right now — I can't sell it, and I won't say it's reserved."`

## add_to_basket (FR-5, FR-12)

```python
def add_to_basket(context: RunContextWrapper[ShopContext], sku: str, qty: int) -> str: ...
```

- **Rules**: `qty >= 1`; unit price copied from the catalogue; `qty > stock` returns
  `"We only have {stock} of {name} — shall I put {stock} aside in this conversation?"` and
  adds nothing (FR-5).
- **Side effect**: appends a `LineItem` to `context.context.basket` (per-session, not shared).

## confirm_order (FR-5)

```python
def confirm_order(context: RunContextWrapper[ShopContext]) -> str: ...
```

- **Behaviour**: builds an `Order` from the basket with a Python-generated `order_id`,
  recomputes the total, and returns a summary sentence. A mismatch between the order agent's
  stated total and the recomputed one is reported in the returned sentence, never silently
  accepted (FR-5).
- **Note**: the structured `Order` itself is the order agent's `output_type`; this tool is the
  side-effecting step that materialises it into the session.

## seasonal_offer — statically off (FR-7)

```python
def seasonal_offer(context: RunContextWrapper[ShopContext]) -> str: ...
# constructed with is_enabled=False
```

- **Contract**: absent from every generated tool schema, in every tier, for the whole life of
  the process. It is never offered and cannot be called.

## loyalty_quote — earned by tier (FR-7)

```python
def loyalty_quote(context: RunContextWrapper[ShopContext]) -> str: ...
# constructed with is_enabled=lambda ctx, agent: ctx.context.tier == "regular"
```

- **Contract**: present in the tool schema only when `tier == "regular"`; absent for a
  walk-in, which the model cannot distinguish from a tool that does not exist.

## re_quote — run-level model override (FR-1)

```python
def re_quote(context: RunContextWrapper[ShopContext], sku: str) -> str: ...
```

- **Behaviour**: runs a nested Desk-priced check with
  `RunConfig(model="gpt-5-mini")` for that single run only, returning a figure. This is the
  third configuration level and exists to be pointed at during review.

## pricing_specialist — an agent exposed as a tool (FR-8)

See `agents.md`. Declared here for completeness: its output is a figure, not prose.
