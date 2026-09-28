# Feature Specification: Shop Desk

**Feature Branch**: `001-shop-desk`
**Created**: 2026-09-28
**Status**: Draft
**Input**: User description: "Shop Desk: a customer-service desk for a small shop that answers stock and price questions from a catalogue, builds a typed order when the customer confirms, and hands genuinely stuck conversations to a human."

## Clarifications

### Session 2026-09-28

- Q: FR-8 requires a turn ceiling — which ceiling should the Desk run under? → A: 10 turns per conversation.
- Q: FR-12 requires a history-trimming rule — what should it drop first? → A: Keep the first user message and the most recent 6 exchanges; discard tool-call items first.
- Q: Which agent should carry the agent-level cheap-override? → A: A dedicated order agent, invoked when the customer confirms, so the Desk itself stays on the process default.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask what something costs (Priority: P1)

A customer asks what an item costs or whether it is in stock. The Desk answers from the
shop's catalogue file, in one turn, without spending a reasoning model on a lookup and
without inventing a figure. The same question asked after closing time is answered with
the correct promise about when the shop can help.

**Why this priority**: this is the cheapest and most frequent conversation the Desk has, and
the one where an invented price does the most damage. It is the project's reason for
existing.

**Independent Test**: ask a price question for a catalogue item and for a non-catalogue
item; check the answer, the number of model calls it cost, and the same question at two
different simulated hours.

**Acceptance Scenarios**:

1. **Given** a catalogue containing an electric kettle, **When** the customer asks its price, **Then** the answer states exactly the catalogue price and the conversation cost exactly one model call.
2. **Given** an item that is not in the catalogue, **When** the customer asks its price, **Then** the Desk says it cannot confirm that item rather than estimating a figure.
3. **Given** an item with zero stock, **When** the customer asks about it, **Then** the Desk reports it as unavailable rather than selling it.
4. **Given** the same price question asked outside shop hours, **When** the Desk answers, **Then** it makes no same-day promise and states when the shop opens.

---

### User Story 2 - Order three of them (Priority: P2)

A customer decides to buy. The Desk confirms the quantity, holds the basket across the
conversation, produces a typed order when the customer confirms, and refuses to quote a
price or identifier that is not in the catalogue. Requests the Desk cannot price itself
are referred to a pricing specialist that answers with a figure.

**Why this priority**: it is the revenue path and the first place where a mistyped total or
an out-of-catalogue SKU becomes a real loss.

**Independent Test**: place an order of several items and verify the order structure, the
recomputed total, and the refusal of a planted out-of-catalogue price.

**Acceptance Scenarios**:

1. **Given** a customer who confirms "three kettles", **When** the order is produced, **Then** the result is a structured order with line items, quantities and unit prices, and a total recomputed from those line items rather than taken from the conversation.
2. **Given** a structured order whose stated total disagrees with the recomputed total, **When** the Desk inspects it, **Then** the discrepancy is reported rather than accepted.
3. **Given** a catalogue edited after an answer was produced, **When** the guardrail re-reads the finished answer, **Then** an answer quoting the old price is refused and the customer is told politely.
4. **Given** a customer whose tier is regular, **When** the Desk decides which tools to offer, **Then** the tool set differs from the one offered to a walk-in customer, and the seasonal tool appears in neither.
5. **Given** a request needing a price the Desk cannot derive itself, **When** the pricing specialist is consulted, **Then** the Desk's reply contains the specialist's figure in the Desk's own wording.
6. **Given** a conversation that reaches the turn ceiling, **When** the ceiling is hit, **Then** the conversation ends politely instead of failing.

---

### User Story 3 - Hand over to a human (Priority: P3)

When the Desk is genuinely stuck — the customer is unhappy, the request is outside the
catalogue, or the ceiling was reached — it hands the conversation to a human escalation
agent, stating why as a structured value and carrying only the part of the history the
human actually needs.

**Why this priority**: a handover that dumps the whole tool-call log on a human is the
expensive failure mode this project exists to avoid.

**Independent Test**: force an escalation and inspect the reason value and the before/after
history the specialist receives.

**Acceptance Scenarios**:

1. **Given** a customer who asks for a human, **When** the handoff happens, **Then** the reason arrives as a structured value, not a sentence.
2. **Given** a conversation full of tool calls, **When** the handoff occurs, **Then** the transferred history is filtered of tool noise while retaining what the specialist needs to be useful, and both versions can be shown.

---

### User Story 4 - A long, affordable conversation (Priority: P4)

A customer talks for ten turns or more in a browser. The Desk still remembers the order
under discussion, two browser windows keep separate baskets, and at the end of the
conversation the shopkeeper can see what it cost: turns, tokens, and which model served
each turn, all under one trace.

**Why this priority**: it is what turns a demo into an operated system — knowing what each
turn cost is the point of the project.

**Independent Test**: run an eleven-turn conversation in one window, start a second window,
and read the cost line and the trace.

**Acceptance Scenarios**:

1. **Given** an eleven-turn conversation, **When** the customer refers to the order from turn two, **Then** the Desk still knows which order is meant.
2. **Given** two browser windows, **When** each adds an item, **Then** the baskets are independent.
3. **Given** a finished conversation, **When** the cost line is read, **Then** it reports turns, tokens and the serving model per turn, and distinguishes fast-path turns from reasoning turns, sourced from the run rather than estimated.
4. **Given** a whole customer conversation, **When** tracing is opened, **Then** that conversation is a single trace in which the fast-path turns and the reasoning turns can be identified and the most expensive turn named.

### Edge Cases

- A customer asks the price of an item that existed in the catalogue but was removed mid-conversation.
- A customer asks for a quantity greater than the catalogue stock.
- The catalogue file is missing, unreadable or malformed at startup.
- A tool receives data it cannot use (unknown SKU, non-numeric quantity).
- The customer bargains or asks the Desk to make up a price.
- Two customers in different sessions order the last unit of the same item.
- A conversation continues past the history trim point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-1**: Products MUST live in a single catalogue file and MUST be reachable only through tools. Model configuration MUST exist at exactly three levels: a process-wide cheap default, an agent-level override used by a dedicated order agent (the Desk itself stays on the process default), and a single-run override used by one re-quote path. Removing the process-wide default MUST change exactly one behaviour: the model that answers a plain question.
- **FR-2**: Every run MUST receive a shop context object (shop, currency, customer identifier, tier) that tools read and that MUST NEVER appear in prompt text. A tool's generated interface MUST expose no context parameter.
- **FR-3**: A question answerable from the catalogue alone MUST be answered by the lookup tool's own output, with the model neither seeing the result nor writing a sentence around it. Ordinary questions MUST keep the normal multi-step reasoning loop. The number of model calls per path MUST be stateable.
- **FR-4**: The system instructions MUST be built per turn from context and the clock. Outside shop hours the Desk MUST NOT promise same-day service and MUST state when it opens. The resolved instruction text MUST be printable before any model call.
- **FR-5**: When the customer confirms, the Desk's output MUST be a structured order (identifier, status, line items with SKU/quantity/unit price, total) rather than prose. The total MUST be recomputed in code from the line items, and a mismatch between the stated and recomputed total MUST be reported. A quantity greater than the available stock MUST be refused, with the available quantity stated.
- **FR-6**: An output guardrail MUST read the finished answer and refuse it if it quotes a price or a SKU that is not in the catalogue. This MUST be a comparison against the catalogue data, not a judgement. The refusal MUST be turned into a polite message rather than an error. An out-of-stock item MUST never be sold. An item removed from the catalogue mid-conversation MUST be reported as no longer available, and stock figures MUST be presented as read at the time of the answer, never as a reservation the Desk cannot make.
- **FR-7**: Two distinct tool controls MUST be present: one seasonal tool switched off statically so it appears in no tool interface at all, and one tool offered only to customers whose tier is regular. The same question asked by a walk-in and by a regular customer MUST present different tool sets.
- **FR-8**: A pricing specialist MUST be exposed to the Desk as a tool and MUST answer with a figure rather than a paragraph; the Desk MUST deliver that figure in its own wording. Every conversation MUST run under a turn ceiling of 10 turns that raises on breach, is caught, and ends the conversation politely.
- **FR-9**: The pricing and escalation agents MUST be clones of one base agent, differing only in instructions and model settings. A clone MUST NOT restate a setting it inherits. What clones share and what they own MUST be demonstrable with identity comparisons.
- **FR-10**: Escalation MUST hand the conversation to a human escalation agent with the reason as a structured typed value drawn from a closed set — the item is not in the catalogue, the item is out of stock, the conversation reached its turn ceiling, the customer asked for a human, or the customer is unhappy — and with history filtered so the specialist does not inherit every tool call. What was removed and what the specialist still needs MUST be documented in the specification.
- **FR-11**: Per-conversation hooks MUST add a cost line reporting turns, tokens, and which model served each turn, distinguishing fast-path turns from reasoning turns. Agent-level hooks MUST be attached to the pricing specialist only. A custom runner MUST record each run's model and token count. All figures MUST come from the run context, not estimates.
- **FR-12**: A browser interface MUST hold a conversation of at least ten turns with history carried per session and trimmed past 6 exchanges — keeping the first user message and the most recent 6 exchanges, and discarding tool-call items before anything else. Trimming MUST NOT break recall of the order under discussion, and two sessions MUST NOT share a basket.
- **FR-13**: Tracing MUST be enabled under the shop's own credentials, and one whole customer conversation MUST be one trace in which the fast-path turns, the reasoning turns, and the most expensive turn can be identified.

### Non-Functional Requirements

- **NFR-1**: Secrets MUST live in a gitignored environment file and MUST never be printed. A missing key MUST fail at startup with a single readable sentence, not a stack trace.
- **NFR-2**: Every agent's model configuration MUST be explicit and justified: an agent either declares its own model or is documented in the plan as deliberately inheriting the process default, and a clone MUST NOT restate a setting it inherits. Settings that are not inherited (such as reasoning effort) MUST be declared per agent. The cheap model is the process default and every override MUST be justified in the plan.
- **NFR-3**: No price, stock figure or SKU may reach a customer unless it came from the catalogue during that run.
- **NFR-4**: A tool meeting bad data MUST return a sentence the model can use. A tool that raises is a defect. A catalogue file that is missing or malformed at startup MUST fail with a single readable sentence naming the file.
- **NFR-5**: Version history MUST show the four specification artifacts committed before the first source file.

### Out of Scope (Deliberate Non-Goals)

1. **No order persistence.** Orders live for the conversation only; the Desk does not store them and cannot answer "what did I order last week".
2. **No bargaining guardrail on input.** The Desk does not detect or negotiate discounts; a customer who bargains is answered by the normal loop or escalated.
3. **No fast-path cache.** A repeated price question costs another lookup; nothing is memoised across turns.

### Key Entities

- **Catalogue product**: a sellable item — SKU, name, price, stock — the only permitted source of price and stock truth.
- **Shop context**: the shop identity, currency, customer identifier and tier for the current run; never spoken into a prompt.
- **Line item**: one SKU, a quantity, and the unit price taken from the catalogue.
- **Order**: an identifier, a status (draft, confirmed, escalated), its line items, and a total recomputed from them.
- **Escalation request**: a structured reason plus the trimmed history handed to a human.
- **Cost line**: turns, tokens and serving model per conversation, tagged fast-path or reasoning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A catalogue price question is answered in exactly one model call; an order question takes more, and both counts are shown from two traces.
- **SC-002**: 100% of quoted prices and SKUs trace to the catalogue used in that run; editing one price in the catalogue makes a previously passing answer fail.
- **SC-003**: A planted mismatch between a stated total and the recomputed total is caught and reported 100% of the time.
- **SC-004**: The same question asked by a walk-in and by a regular customer yields two different tool sets; the seasonal tool appears in neither.
- **SC-005**: A conversation of at least eleven turns still identifies the order under discussion, and two browser sessions never share a basket.
- **SC-006**: Every escalation arrives at the human with a structured reason and a transferred history containing **zero tool-call items** — its item count is lower than the full transcript by exactly the number of tool items removed.
- **SC-007**: Every conversation produces a cost line whose figures come from the run, and one openable trace showing the fast-path and reasoning turns.
- **SC-008**: Version history shows the four specification artifacts ahead of the first source file.

## Assumptions

- Single shop, single currency, catalogue held in one file read at run time; no inventory writes during a conversation.
- Customer identity is supplied by the interface/session, not authenticated.
- Tiers are exactly two: walk-in and regular; no loyalty tiers beyond these.
- Shop opening hours are configuration, and a simulated clock is available so hour-dependent behaviour can be demonstrated without waiting.
- The customer-facing language is English.
