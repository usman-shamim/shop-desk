# Contract: Escalation Handoff and Output Guardrail

## Escalation handoff (FR-10)

```python
handoff(
    agent=escalation,                          # the cloned escalation specialist
    input_type=EscalationRequest,              # typed reason, not a sentence
    input_filter=handoff_filters.remove_all_tools,
)
```

**Input contract — `EscalationRequest`**

| Field | Type | Required |
|-------|------|----------|
| `reason` | `Literal["not_in_catalogue", "out_of_stock", "turn_ceiling", "customer_requested_human", "customer_unhappy"]` | yes |
| `summary` | `str` (≤ 200 chars) | yes |
| `basket_snapshot` | `list[LineItem]` | yes |

**History filter — exactly what `remove_all_tools` removes**: function-call items and their
outputs (the Desk's catalogue lookups, basket writes, and specialist calls). Tool arguments
and results therefore do not travel.

**What the specialist still gets**: the system context of the escalation agent, the user's
messages, and the Desk's assistant messages — so the human can see *what was asked and what
was said*, including any figure already quoted in text — plus the typed reason and the basket
snapshot.

**Consequence to state in review**: a price the Desk quoted exists in the transferred history
only as text inside an assistant message, not as a catalogue record. If that matters for a
dispute, the catalogue row must be re-read by the human's own tooling.

**Trigger points**: the five `reason` values above; `turn_ceiling` is raised by
`MaxTurnsExceeded` (10 turns) and caught in `runner.py`, which converts it into the same
typed handoff rather than an error.

## Output guardrail (FR-6)

```python
@output_guardrail
async def catalogue_truth_guardrail(
    ctx: RunContextWrapper[ShopContext], agent: Agent, output: str
) -> GuardrailFunctionOutput: ...
```

- **Check**: extract every price-shaped token and every SKU-shaped token from the finished
  answer; every one must exist in the catalogue loaded for this run (price match exact, SKU
  match case-insensitive). This is a comparison against the file, not a judgement.
- **Pass**: `GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)`.
- **Fail**: `tripwire_triggered=True` with `output_info={"reason": ..., "offending": ...}`.
- **Handling**: the runner catches the guardrail tripwire exception and replies with the
  canonical refusal sentence — never a traceback (FR-6).
- **Demonstrable behaviour**: editing a price in `catalogue.json` makes a previously passing
  answer trip. Removing an item mid-conversation makes an answer referencing it trip as
  "no longer available".
- **Out of scope**: stock reservation language, bargaining, and prompt-injection defence are
  not part of this guardrail (the first two are deliberate non-goals).

## Canonical customer-visible sentences

These strings live in `shopdesk/messages.py` and are the **only** wording used for these
situations; tests and demo checks assert against them, so "polite" is a fixed string rather
than an implementation choice.

| Situation | Exact sentence |
|-----------|----------------|
| Guardrail refusal (price or SKU not in the catalogue) | `I can't confirm that price from our catalogue, so I won't quote it — a colleague can check it for you.` |
| Out of stock | `That item is out of stock right now, so I can't sell it — I won't hold it without checking.` |
| Item removed from the catalogue mid-conversation | `That item isn't in our catalogue any more, so I can't price it.` |
| Turn ceiling reached (10 turns) | `I'm sorry — I've taken this as far as I can. I'm passing you to a colleague who can finish it with you.` |
| Escalation acknowledgement | `I'm handing you to a colleague now, and they have what they need.` |
| Quantity beyond stock | `We only have {stock} of {name} — I can put {stock} in this conversation if that helps.` |
