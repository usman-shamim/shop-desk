# Contract: Agents

| Agent | Model | Instructions source | Output | Tools | Hooks |
|-------|-------|--------------------|--------|-------|-------|
| `desk` | *none declared* → process default (`OPENAI_DEFAULT_MODEL=gpt-5-nano`) | `instructions.py` callable (context + clock, FR-4) | text | price/stock lookup, basket tools, `pricing_specialist`, loyalty (tier-gated), seasonal (off) | run-level only |
| `order_assembler` | `gpt-5-mini` (**agent-level override**, FR-1) | static, order-specialised | `Order` (pydantic, FR-5) | `add_to_basket`, `confirm_order` | — |
| `pricing` | *none declared* (inherits default) | specialist: answer with a figure only | text (a number) | — | `PricingAgentHooks` (**only here**, FR-11) |
| `escalation` | *none declared* (inherits default) | human-handoff voice | text | — | — |

## `desk`

- **Contract**: answers customer turns; must never state a price or SKU not produced by a
  tool this run; ends the turn normally except when the price fast path applies (FR-3).
- **Tool visibility**: `seasonal_offer` never present; `loyalty_quote` present only for
  `tier == "regular"` (FR-7).
- **Handoff**: may hand off to `escalation` with an `EscalationRequest` (FR-10).
- **Guardrail**: every finished answer passes the catalogue output guardrail (FR-6).

## `order_assembler`

- **Contract**: invoked when the customer confirms; returns a validated `Order`. Its `total`
  is advisory — the stated and recomputed totals are compared and a mismatch reported.
- **Why the override**: multi-turn order assembly and validation is the one place the project
  deliberately spends a stronger model (justification for NFR-2 in `plan.md`).

## `base_specialist` and its clones (FR-9)

```python
base_specialist = Agent(name="specialist", instructions=BASE_INSTRUCTIONS, tools=[...])
pricing    = base_specialist.clone(instructions=PRICING_INSTRUCTIONS, model_settings=ModelSettings(...))
escalation = base_specialist.clone(instructions=ESCALATION_INSTRUCTIONS, model_settings=ModelSettings(...))
```

- **Shared (identical object identity, shown with `is`)**: `tools`, `handoffs`,
  `output_type`, and any other field not overridden.
- **Owned (distinct objects)**: `instructions` and `model_settings` on each clone.
- **Neither clone restates a model**, so both inherit the process default (FR-9, FR-1).
- **Sharing to watch**: the `tools` list is the same object in both clones — mutating one
  clone's list in place would silently change the other, so tools are treated as immutable
  after construction.

## `pricing` exposed as a tool (FR-8)

```python
pricing_tool = pricing.as_tool(
    tool_name="pricing_specialist",
    tool_description="Get a definitive price figure for a catalogue item.",
    custom_output_extractor=extract_figure,   # returns only the number
)
```

- **Contract**: returns a figure the Desk re-words into its own sentence. Prose from the
  specialist must not reach the customer verbatim.
- **Nested run**: bounded by the same turn ceiling, and its usage is recorded by the custom
  runner (FR-11).
