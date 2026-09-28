# ADR-0002: Tool-Output Fast Path for Catalogue Price Answers

> **Scope**: How the Desk produces a customer-facing answer that is a catalogue fact — the
> routing mechanism, what it costs, and what it gives up.

- **Status:** Accepted
- **Date:** 2026-09-28
- **Feature:** 001-shop-desk
- **Context:** A price question is the most frequent and cheapest conversation the Desk has,
  and an invented price is the most damaging failure it can produce. The specification
  requires that a question answerable from the catalogue alone be answered by the lookup
  tool's own output, with the model neither seeing the result nor writing a sentence around
  it, while ordinary questions keep the normal reasoning loop. The SDK's default tool-use
  behaviour feeds tool results back to the model for another call; it also supports ending the
  run on a tool's output.

## Decision

The Desk agent configures its tool-use behaviour so that a call to the catalogue price lookup
**ends the run with that tool's output as the final answer**. Concretely: a
`ToolsToFinalOutputFunction` returns a final output when the called tool is `lookup_price`
(the declarative form of the same decision is stopping at that tool name).

Consequences for the shape of the answer: the customer receives the tool's sentence verbatim
— a catalogue value by construction, in one model call. Every other question path leaves the
default behaviour untouched and loops normally.

## Consequences

### Positive

- A catalogue price answer costs **one** model call and cannot be invented: the number is
  never inside a model's context to begin with.
- The cost line and the trace show a visibly different path from reasoning turns, which makes
  the project's central claim demonstrable rather than asserted.
- Deleting the behaviour restores ordinary behaviour with a one-line change, so the trade-off
  can be shown live in review.

### Negative

- **We give up the model's phrasing.** The customer gets the tool's wording — no greeting
  tailoring, no empathy, no suggestion of a cheaper alternative, no handling of a compound
  question ("how much is the kettle, and do you deliver to Lahore?") in the same turn. The
  second half of such a question either waits for the next turn or is lost.
- The tool's sentence becomes customer-visible UI copy, so tool wording and product tone are
  now coupled — a change to a tool message is a change to the customer experience.
- The fast path is defined by a tool name, so renaming the tool silently disables it unless the
  behaviour function is updated with it.

## Alternatives Considered

- **Default loop (tool result fed back to the model)**: better phrasing, but a second model
  call per price question, and the model is handed the catalogue value — reintroducing exactly
  the invention risk the project exists to remove. Rejected.
- **Short-circuit before any model call** (pattern-match the question and answer directly):
  zero model calls, but the Desk can no longer route intent, cannot handle a price question
  with a follow-up, and the "one call versus many" comparison in the trace disappears. Rejected.
- **Cache the tool result instead of routing around the model**: saves the second call only on
  repeats and leaves the model writing the sentence — it is an optimisation of the wrong
  thing, and caching is an explicit non-goal of this feature. Rejected.
- **Post-hoc guardrail only** (let the model answer, then check it): cheaper to build, but it
  detects invented prices rather than preventing them, and still spends the second call.
  Rejected as the primary mechanism — the guardrail is retained as a second line of defence.

## References

- Feature Spec: [spec.md](../specs/001-shop-desk/spec.md) §FR-3, §FR-6, §SC-001
- Implementation Plan: [plan.md](../specs/001-shop-desk/plan.md) "Complexity Tracking", contract
  [contracts/tools.md](../specs/001-shop-desk/contracts/tools.md)
- Related ADRs: ADR-0001 (three-level model configuration)
- Evaluator Evidence: history/prompts/001-shop-desk/
