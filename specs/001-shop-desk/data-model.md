# Phase 1 Data Model: Shop Desk

Types are defined with `pydantic` (structures crossing a LLM/tool boundary) or `dataclasses`
(context objects the model never sees). Field notes name the requirement each rule serves.

## ShopContext (dataclass — never serialised into a prompt)

| Field | Type | Notes |
|-------|------|-------|
| `shop` | `str` | shop display name, from catalogue metadata |
| `currency` | `str` | ISO-style code, from catalogue metadata |
| `customer_id` | `str` | session-scoped identifier; must not appear in prompt text (FR-2) |
| `tier` | `str` | `"walk_in"` or `"regular"`; drives tool visibility (FR-7) |
| `basket` | `list[LineItem]` | lines the customer has agreed to so far (FR-5, FR-12) |
| `orders` | `list[Order]` | orders built this session; in-memory only (non-goal: no persistence) |
| `turns` | `int` | completed turns, for the cost line (FR-11) |
| `escalated` | `bool` | set when a handoff has occurred, to prevent loops (FR-10) |

**Validation / rules**: `tier` MUST be one of the two values; `customer_id` MUST NOT be
interpolated into any instruction string (checked by grep in the DoD).

## Product (catalogue entry — read-only)

| Field | Type | Notes |
|-------|------|-------|
| `sku` | `str` | unique; any SKU in an answer must exist here (FR-6, NFR-3) |
| `name` | `str` | display name |
| `price` | `float` | the only permitted source of a quoted price (NFR-3) |
| `stock` | `int` | read at the moment of the answer; never presented as a reservation (FR-6) |

**Source**: `catalogue.json` — `{ "shop": str, "currency": str, "products": [Product] }`.
**Rules**: missing or malformed file → one readable startup sentence (NFR-4). Zero stock
is not sellable (FR-6). A SKU removed mid-conversation is reported unavailable (FR-6).

## LineItem (pydantic)

| Field | Type | Notes |
|-------|------|-------|
| `sku` | `str` | must resolve in the catalogue at build time |
| `qty` | `int` | `ge=1`; `gt` available stock is refused with the available quantity stated (FR-5) |
| `unit_price` | `float` | copied from the catalogue entry, never from the model (FR-5, NFR-3) |

## Order (pydantic — the structured output of the order agent)

| Field | Type | Notes |
|-------|------|-------|
| `order_id` | `str` | generated in Python, not by the model |
| `status` | `Literal["draft", "confirmed", "escalated"]` | see transitions below |
| `items` | `list[LineItem]` | at least one item to be confirmable |
| `total` | `float` | the model's figure; compared against `recompute_total`, mismatch reported (FR-5) |

**Derived**: `recompute_total(order) -> float = sum(i.qty * i.unit_price)` — the only total
the Desk may state.
**State transitions**: `draft` --customer confirms--> `confirmed`; `draft` --escalation-->
`escalated`; `confirmed` is terminal within a session (no cancellation is in scope).

## EscalationRequest (pydantic — typed handoff input)

| Field | Type | Notes |
|-------|------|-------|
| `reason` | `Literal["not_in_catalogue", "out_of_stock", "turn_ceiling", "customer_requested_human", "customer_unhappy"]` | closed set (FR-10) |
| `summary` | `str` | one line of context for the human, ≤ 200 chars |
| `basket_snapshot` | `list[LineItem]` | what the customer had chosen, so the human need not ask |

## CostLine (in-memory, printed; rows also appended to `costs.jsonl`)

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | `str` | groups a conversation and its trace (FR-13) |
| `turn_index` | `int` | 1-based |
| `model` | `str` | the model that actually served the turn (FR-11) |
| `path` | `Literal["fast_path", "reasoning"]` | fast path = the turn ended on the catalogue tool's output (FR-3, FR-11) |
| `input_tokens` / `output_tokens` | `int` | read from run usage, never estimated (FR-11) |

## SessionState (Chainlit, per `cl.user_session`)

| Field | Type | Notes |
|-------|------|-------|
| `context` | `ShopContext` | one per browser window, so windows do not share a basket (FR-12) |
| `history` | `list[item]` | SDK item list carried between turns |
| `trimmed_at` | `int` | count of exchanges dropped, for the before/after report (FR-12) |

**Trim rule (FR-12)**: keep the first user message plus the most recent six exchanges;
discard tool-call and tool-output items before any user or assistant message.

## Trace mapping (FR-13)

One conversation = one trace: `trace(workflow_name="shop-desk", group_id=session_id)`
wrapping every turn of the session, with nested specialist runs inside it.
