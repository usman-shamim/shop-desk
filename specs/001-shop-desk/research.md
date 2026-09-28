# Phase 0 Research: Shop Desk

Each decision below resolves a mechanism the design depends on. Format: **Decision** /
**Rationale** / **Alternatives considered**.

## R1 — Global process default model

**Decision**: set the process default with the `OPENAI_DEFAULT_MODEL` environment variable
in `.env`, loaded by `python-dotenv` in `config.py` before any client is constructed.
**Rationale**: the SDK resolves a model for an agent that declares none through this
variable; it is genuinely process-wide, and it disappears when the line is deleted, which
is exactly FR-1's "watch one behaviour change" check. It also keeps the cheap model out of
code, satisfying NFR-2.
**Alternatives considered**: `set_default_openai_client` with a custom client (does not
choose a model); passing a model to every agent (loses the global level entirely).

## R2 — Agent-level override

**Decision**: the dedicated order agent declares `model="gpt-5-mini"` on itself; no other
agent declares a model.
**Rationale**: FR-1 requires the override to live on the agent that must reason about an
order, and FR-9 requires clones not to restate an inherited setting — so the Desk and both
specialists stay silent about their model.
**Alternatives considered**: overriding on the Desk (a price question would then cost the
stronger model — contradicts FR-3); an environment variable for the stronger model (would
have created a second implicit global level).

## R3 — Run-level override

**Decision**: the re-quote path passes `RunConfig(model="gpt-5-mini")` to that single
`Runner.run` call.
**Rationale**: `RunConfig.model` is scoped to one run and cannot leak into later turns,
making it the honest third level.
**Alternatives considered**: temporarily mutating the Desk agent's model (not thread-safe
across Chainlit sessions); a separate agent for re-quotes (a fourth level in disguise).

## R4 — Shop context invisible to the model (FR-2)

**Decision**: `ShopContext` is a dataclass passed as the run context; tools declare
`context: RunContextWrapper[ShopContext]` as their first parameter, and dynamic
instructions read it through the run-context wrapper.
**Rationale**: the SDK excludes a `RunContextWrapper` parameter from the generated tool
schema and never serialises it into prompt text, which is precisely FR-2's done-when
(generated schema has no context parameter; grepping prompts finds no customer id).
**Alternatives considered**: injecting context into the instruction string (leaks the
customer id and breaks the grep check); a module-level global (breaks per-session
isolation, FR-12).

## R5 — Fast path: one model call for a price answer (FR-3)

**Decision**: the Desk agent sets
`tool_use_behavior` to stop on the price-lookup tool and treat **that tool's output as the
final output** (implemented as a `ToolsToFinalOutputFunction` that returns the final output
when the called tool is `lookup_price`; `StopAtTools(stop_at_tool_names=[...])` is the
declarative form of the same idea).
**Rationale**: the loop then ends after the first model call that requests the lookup, so
the model neither sees the catalogue figure nor writes a sentence around it — one model
call, and the answer is a catalogue value by construction.
**Alternatives considered**: the default `run_llm_again` (a second model call to phrase the
answer, and a chance to invent a price); a custom `Runner` that short-circuits before the
model (zero model calls, but then nothing routes intent — the tests and the trace would no
longer show a turn, and the Desk loses the ability to answer the follow-up questions real
customers ask).
**Trade-off to state on demand**: we give up the Desk's own phrasing of a price — no
politeness wrapping, no suggestion of an alternative product, no handling of a compound
question in the same turn.

## R6 — Dynamic instructions (FR-4)

**Decision**: pass a callable as `instructions` that receives the run context and returns
the resolved prompt, built from shop, currency, tier and the (possibly simulated) clock.
**Rationale**: the SDK calls it per turn with the live context, so hours-aware promises need
no prompt mutation elsewhere; the same function is reused by the `--print-prompt` flag to
show the resolved text before any model call.
**Alternatives considered**: a static prompt with a time placeholder the model must
interpret (untestable); regenerating the agent per turn (loses clone identity, FR-9).

## R7 — Structured order and recomputed total (FR-5)

**Decision**: the order agent declares `output_type=Order` (pydantic); the total is
recomputed in Python from line items by `recompute_total`, and any mismatch with the model's
figure is reported rather than silently corrected.
**Rationale**: structured output makes "a confirmed order is a structure, not prose" a type
guarantee, and recomputation in Python is the only way a planted mismatch can be caught.
**Alternatives considered**: parsing JSON out of prose (fragile); trusting the model's total
(fails the audited check).

## R8 — Output guardrail checked against data (FR-6)

**Decision**: an `@output_guardrail` extracts price and SKU tokens from the finished answer
and compares them with the catalogue loaded for that run; a mismatch raises the guardrail
tripwire, which the runner catches and converts into a polite message.
**Rationale**: the check is a set comparison against the file, so editing a catalogue price
makes a previously passing answer fail — the demonstrable behaviour FR-6 requires.
**Alternatives considered**: a model-based judge (non-deterministic, and it would spend a
model call on the check); regex-free string search for any number (would reject legitimate
quantities).

## R9 — Tools off and tools earned (FR-7)

**Decision**: the seasonal tool is constructed with `is_enabled=False`; the loyalty tool is
constructed with a callable `is_enabled` that returns `tier == "regular"`.
**Rationale**: disabled tools are completely hidden from the LLM at runtime — the model
cannot see, cannot name, and cannot call them — which is why "off" and "not offered" are the
same thing to the model: both are an absence from the tool list, not a refusal.
**Alternatives considered**: a tool that returns "not available" (visible, costs a call, and
tells a walk-in customer that a loyalty scheme exists); filtering the tool list per request
(equivalent for the callable case, but static `False` is clearer for the seasonal one).

## R10 — Pricing specialist as a tool that returns a figure (FR-8)

**Decision**: `pricing_agent.as_tool(tool_name="pricing_specialist", ...)` with a
`custom_output_extractor` that returns only the figure from the specialist's run, and
instructions that forbid prose.
**Rationale**: as-a-tool (not a handoff) keeps control with the Desk, so the Desk answers in
its own wording while the specialist supplies the number — exactly FR-8's wording.
**Alternatives considered**: a handoff (the specialist would then own the reply, and the
customer would hear the specialist's voice); asking the Desk model to compute the price
itself (no catalogue authority).

## R11 — Turn ceiling (FR-8)

**Decision**: every `Runner.run` passes `max_turns=10`; the resulting
`MaxTurnsExceeded` exception is caught in `runner.py` and turned into a polite hand-off
message.
**Rationale**: the SDK's own ceiling mechanism raises rather than hanging, and catching it
is what makes "raises, is caught, ended politely" true.
**Alternatives considered**: counting turns in application code (duplicates a mechanism the
SDK owns); no ceiling (an unbounded conversation is an unbounded bill).

## R12 — Clones from one base (FR-9)

**Decision**: `base_specialist = Agent(name=..., instructions=..., tools=[...])`, then
`pricing = base_specialist.clone(instructions=..., model_settings=...)` and
`escalation = base_specialist.clone(instructions=..., model_settings=...)`; the clones never
name a model.
**Rationale**: `clone()` copies fields wholesale, so the shared attribute identities are
demonstrable with `is`, and only the two overridden fields differ — the exact comparison FR-9
asks for.
**Alternatives considered**: two independently constructed agents (no sharing to
demonstrate); subclassing (adds a type hierarchy for no behavioural gain).

## R13 — Handoff with typed reason and filtered history (FR-10)

**Decision**: `handoff(agent=human_escalation, input_type=EscalationRequest,
input_filter=handoff_filters.remove_all_tools)`, where `EscalationRequest` carries the
reason as a `Literal` from the closed set in the spec plus a one-line summary.
**Rationale**: `input_type` makes the reason a typed value at the handoff boundary, and the
SDK's `remove_all_tools` filter strips function-call and tool-output items — the Desk's tool
noise — while leaving the user and assistant messages the human needs.
**Alternatives considered**: passing the reason as a sentence in the handoff message (not
typed, not checkable); writing a bespoke filter (more code for the same result, though the
spec allows it).
**Consequence to state**: after filtering, the specialist sees the conversation without the
catalogue lookups; if a price was quoted, the value survives only as text in the assistant's
message, not as a tool record.

## R14 — Cost line and custom runner (FR-11)

**Decision**: a `RunHooks` subclass accumulates per-turn records (model name, token usage,
whether the turn took the fast path) and prints the cost line at conversation end; an
`AgentHooks` subclass is attached to the **pricing clone only**; a
`CostTrackingRunner(Runner)` subclass records each run's model and token count to
`costs.jsonl`.
**Rationale**: hooks receive the live run context, so the numbers are read from usage rather
than estimated, and the fast-path/reasoning split falls out of the model name plus whether
the turn ended on the tool output.
**Alternatives considered**: parsing logs (estimates, and silently wrong when the SDK
changes its logging); a wrapper around every call site (misses nested specialist runs).

## R15 — One trace per conversation (FR-13)

**Decision**: tracing stays on (default) with the key from `.env`; each conversation wraps
its turns in a single `trace(workflow_name="shop-desk", group_id=<session_id>)`.
**Rationale**: grouping by session id makes one customer conversation one trace with the
Desk's turns, the fast-path turns and the nested specialist runs inside it.
**Alternatives considered**: per-turn traces (the "one conversation, one trace" claim would
fail); disabling tracing to save cost (it is the evidence for the cost claims).

## R16 — Browser session, per-session state, trim rule (FR-12)

**Decision**: Chainlit, with `ShopContext` and history held in `cl.user_session`; history is
trimmed to the first user message plus the most recent six exchanges, dropping tool-call
items first.
**Rationale**: session-scoped storage gives each browser window its own context and basket
(two windows cannot share a basket), and the trim rule keeps the customer's original ask and
recent context while discarding what is re-derivable from live order state.
**Alternatives considered**: trimming oldest-first including user messages (loses the
product under discussion); summarising dropped turns with a model call (costs a call, which
this project is about not doing).

## R17 — Tool failures return sentences (NFR-4)

**Decision**: every function tool sets `failure_error_function` to a shop-voiced sentence
function, and each tool body additionally guards unknown SKU, unparseable quantity, and
missing stock.
**Rationale**: the SDK's default error function already returns a message to the model
instead of raising; a custom one keeps the Desk's voice consistent and makes the NFR-4 claim
visible in code.
**Alternatives considered**: catching exceptions in the runner (leaves the tool as a defect
by the constitution's definition); returning empty strings (the model then invents).
