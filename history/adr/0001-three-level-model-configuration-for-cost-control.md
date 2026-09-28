# ADR-0001: Three-Level Model Configuration for Cost Control

> **Scope**: The model-configuration mechanism as a whole — the process default, the two
> permitted overrides, and which call sites own them. Not individual model ids.

- **Status:** Accepted
- **Date:** 2026-09-28
- **Feature:** 001-shop-desk
- **Context:** The Desk answers two very different workloads: catalogue lookups (frequent,
  simple, answerable from a file) and order assembly (rare, multi-turn, requires reasoning
  over a conversation and validation of a typed structure). The specification forbids
  spending a reasoning model on a price question, requires exactly three levels of model
  configuration, and requires every override to be justified. The SDK resolves a model that
  an agent does not declare from the process-wide `OPENAI_DEFAULT_MODEL` variable, resolves a
  declared one from the agent, and lets a single run override both.

## Decision

Model configuration exists at exactly three levels, each with one named owner:

- **Process / global**: `OPENAI_DEFAULT_MODEL=gpt-5-nano` in `.env`, loaded by
  `python-dotenv` before the first model call. The Desk, the pricing specialist and the
  escalation specialist declare no model and inherit this.
- **Agent**: the dedicated `order_assembler` agent declares `model="gpt-5-mini"`. It exists
  solely for the confirmation step and is the only agent that names a model.
- **Run**: the re-quote path passes `RunConfig(model="gpt-5-mini")` to one `Runner.run` call,
  scoped to that run and unable to leak into later turns.

Deleting the process default must change exactly one observable behaviour: the model that
answers a plain question.

## Consequences

### Positive

- The cost of a turn is decided by *where* the code lives, not by a prompt instruction, so it
  is reviewable by reading three lines in three files.
- Removing the global default is a live demonstration of the layering, not a claim about it.
- Specialists stay model-agnostic, so changing the cheap model is a one-line environment
  change with no code edits.
- The re-quote override proves override scope: one run, no leakage.

### Negative

- Three places must stay coordinated; a fourth implicit level (for example, a model id
  hard-coded inside the runner) would silently break the story, so the code must be audited
  for stray model literals.
- The stronger model is deliberately *not* used for the Desk's own probability of answering a
  tricky question well — a hard question outside the catalogue costs escalation rather than a
  better model.
- Costs are optimisation-visible but not enforced: nothing prevents a future caller from
  passing a strong model in a `RunConfig`.

## Alternatives Considered

- **Single global model for everything**: simplest, but either a price question costs the
  stronger model (violates the cost theme) or order assembly runs on the cheap model (risks
  malformed orders). Rejected.
- **Per-agent model on every agent**: explicit, but turns three levels into one level plus
  duplication, and loses the ability to demonstrate "delete the global default and watch one
  behaviour change". Rejected.
- **Two environment variables (cheap and strong)**: keeps models out of code entirely, but
  creates a de-facto second global level and hides the agent/run distinction the
  specification asks to be pointable. Rejected.
- **Prompt-based cost control** ("use your cheapest judgement"): unverifiable and unenforced.
  Rejected.

## References

- Feature Spec: [spec.md](../specs/001-shop-desk/spec.md) §FR-1, §NFR-2
- Implementation Plan: [plan.md](../specs/001-shop-desk/plan.md) "Model Configuration (FR-1)"
- Related ADRs: ADR-0002 (the fast path that keeps price questions to one call)
- Evaluator Evidence: history/prompts/001-shop-desk/
