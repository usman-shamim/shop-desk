---
description: "Task list for Shop Desk (001-shop-desk)"
---

# Tasks: Shop Desk

**Input**: Design documents from `/specs/001-shop-desk/`
**Prerequisites**: plan.md, spec.md (user stories), research.md, data-model.md, contracts/, quickstart.md
**Tests**: INCLUDED — the specification's Definition of Done requires demonstrated checks
(call counts, planted mismatch, guardrail trip, history filtering), so test tasks are part of
each story rather than optional.

**Organization**: tasks are grouped by user story so each story can be implemented, tested and
demonstrated on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different file, no dependency on an incomplete task)
- **[Story]**: which user story the task serves (US1–US4)
- Every task names the requirement it serves (`FR-n` / `NFR-n`) and the exact file path

## Path Conventions

Single project: package modules in `shopdesk/`, entry points at the repository root, tests in
`tests/`, demo evidence in `scripts/demo_checks.py`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: project skeleton and configuration surface

- [ ] T001 Create the package skeleton `shopdesk/__init__.py`, empty `tests/` and `scripts/` directories, and `requirements.txt` pinning `openai-agents`, `python-dotenv`, `chainlit`, `pytest`
- [ ] T002 [P] Write `.env.example` documenting `OPENAI_API_KEY`, `OPENAI_DEFAULT_MODEL=gpt-5-nano`, `SHOP_OPEN_HOUR`, `SHOP_CLOSE_HOUR`, `SHOP_SIMULATED_HOUR`, `TURN_CEILING=10`, `CATALOGUE_PATH` (NFR-1, FR-1, FR-4, FR-8)
- [ ] T003 [P] Create `catalogue.json` with the sample shop metadata and products (`KTL-01` kettle 4200/12, `FAN-22` pedestal fan 9800/0, plus two normal items) (FR-1, NFR-3)
- [ ] T004 [P] Add `.env` to `.gitignore` verification and a `pyproject.toml`/`pytest.ini` test configuration (NFR-1)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the shared pieces every story needs — context, catalogue truth, typed structures, the run facade

**⚠️ No user story work can begin until this phase is complete**

- [ ] T005 Implement `shopdesk/config.py`: `load_dotenv()`, fail at startup with one readable sentence when a required key is missing, expose shop hours and the simulated clock (NFR-1, FR-4)
- [ ] T006 [P] Implement `shopdesk/context.py`: `ShopContext` dataclass with `shop`, `currency`, `customer_id`, `tier`, `basket`, `orders`, `turns`, `escalated` (FR-2, FR-12)
- [ ] T007 [P] Implement `shopdesk/catalogue.py`: load `catalogue.json` once per run, expose `find(sku)` and `all_products()`, return one readable sentence on a missing/malformed file (FR-1, NFR-3, NFR-4)
- [ ] T008 [P] Implement `shopdesk/orders.py`: `LineItem`, `Order` pydantic models and `recompute_total(order)` returning the Python-derived total (FR-5)
- [ ] T009 Implement `shopdesk/agents.py`: `base_specialist` plus `pricing`/`escalation` clones via `clone()`, with a `show_clone_identity()` helper printing `is` comparisons for shared and owned attributes (FR-9)
- [ ] T010 Implement `shopdesk/runner.py`: the per-turn facade — build context, wrap the turn in a trace group, pass `max_turns`, and centralise exception handling so nothing raises into the caller (FR-8, FR-13)
- [ ] T011 Implement `shopdesk/instructions.py`: the dynamic instruction callable built from context and the clock, plus `resolve_prompt(context)` used by the `--print-prompt` flag (FR-4)

**Checkpoint**: foundation ready — stories can now proceed in parallel.

---

## Phase 3: User Story 1 — Ask what something costs (Priority: P1) 🎯 MVP

**Goal**: a catalogue price or stock question is answered from the file in exactly one model call, with the model never seeing the value, and the promise made outside shop hours is correct.

**Independent Test**: ask "what does the kettle cost?" for a catalogue item, a non-catalogue item and an out-of-stock item; read the call count and repeat at `--hour 21`.

### Tests for User Story 1 ⚠️ (write first, ensure they fail)

- [ ] T012 [P] [US1] Test `lookup_price`/`lookup_stock` return catalogue values and, for an unknown SKU, a sentence rather than an exception, in `tests/test_tools.py` (FR-3, NFR-4)
- [ ] T013 [P] [US1] Test that the price lookup appears in the generated tool schema with **no** context parameter, in `tests/test_tool_visibility.py` (FR-2)

### Implementation for User Story 1

- [ ] T014 [US1] Implement `lookup_price` and `lookup_stock` in `shopdesk/tools.py` with `RunContextWrapper[ShopContext]` first parameter and `failure_error_function=shop_style_error` (FR-2, FR-3, NFR-4)
- [ ] T015 [US1] Implement the fast path in `shopdesk/fastpath.py`: a `ToolsToFinalOutputFunction` that ends the run on the price lookup's own output, and tags the turn as `fast_path` (FR-3, FR-11)
- [ ] T016 [US1] Wire the Desk agent in `shopdesk/agents.py`: no declared model, the catalogue tools, `tool_use_behavior` from T015, dynamic instructions from T011 (FR-1, FR-3, FR-4)
- [ ] T017 [US1] Implement the hours-aware promise in `shopdesk/instructions.py`: outside hours, no same-day promise and the opening time is stated (FR-4)
- [ ] T018 [US1] Implement `main.py` CLI REPL with `--tier`, `--hour` and `--print-prompt` flags routed through `runner.py` (FR-4, FR-12)
- [ ] T019 [US1] Add `price-call-count` to `scripts/demo_checks.py`: assert one model call for a price question and more for an order question, from the recorded cost line (FR-3, SC-001)

**Checkpoint**: US1 is independently demonstrable — the MVP.

---

## Phase 4: User Story 2 — Order three of them (Priority: P2)

**Goal**: a confirmation produces a typed order with a Python-recomputed total; no price or SKU reaches the customer unless it is in the catalogue; the tool sets differ by tier; hard pricing goes to a specialist under a turn ceiling.

**Independent Test**: order several items, plant a wrong total, edit a catalogue price, and ask the same question as `walk_in` and as `regular`.

### Tests for User Story 2 ⚠️ (write first, ensure they fail)

- [ ] T020 [P] [US2] Test that a planted mismatch between stated and recomputed total is reported, in `tests/test_orders.py` (FR-5, SC-003)
- [ ] T021 [P] [US2] Test the guardrail passes a catalogue-true answer and trips on a stranger price after the catalogue is edited, in `tests/test_guardrails.py` (FR-6, SC-002)
- [ ] T022 [P] [US2] Test tool visibility by tier: seasonal absent for both tiers, loyalty present only for `regular`, in `tests/test_tool_visibility.py` (FR-7, SC-004)

### Implementation for User Story 2

- [ ] T023 [US2] Implement `add_to_basket` and `confirm_order` in `shopdesk/tools.py`, including the quantity-over-stock refusal with the available quantity stated (FR-5)
- [ ] T024 [US2] Add the `order_assembler` agent in `shopdesk/agents.py` with `model="gpt-5-mini"` and `output_type=Order` — the agent-level override (FR-1, FR-5)
- [ ] T025 [US2] Implement the catalogue output guardrail in `shopdesk/guardrails.py` and catch the tripwire in `shopdesk/runner.py`, converting it into a polite message (FR-6)
- [ ] T026 [US2] Add the seasonal tool with `is_enabled=False` and the loyalty tool with a tier-callable `is_enabled` in `shopdesk/tools.py` (FR-7)
- [ ] T027 [US2] Implement the pricing specialist in `shopdesk/pricing.py` and expose it with `as_tool(..., custom_output_extractor=...)` returning only the figure (FR-8)
- [ ] T028 [US2] Wire the 10-turn ceiling in `shopdesk/runner.py` and catch `MaxTurnsExceeded` into a polite end-of-conversation message (FR-8)
- [ ] T029 [US2] Implement the re-quote path in `shopdesk/tools.py` using `RunConfig(model="gpt-5-mini")` for that single run — the run-level override (FR-1)
- [ ] T030 [US2] Add `catalogue-edit` and `total-mismatch` checks to `scripts/demo_checks.py` (SC-002, SC-003)

**Checkpoint**: US1 and US2 both work independently.

---

## Phase 5: User Story 3 — Hand over to a human (Priority: P3)

**Goal**: an escalation carries a typed reason and a history stripped of tool noise.

**Independent Test**: force each of the five triggers and inspect the reason value plus the before/after history.

### Tests for User Story 3 ⚠️

- [ ] T031 [P] [US3] Test that the handoff input is an `EscalationRequest` with a reason from the closed set, in `tests/test_escalation.py` (FR-10)
- [ ] T032 [P] [US3] Test that filtering removes tool-call and tool-output items while preserving user and assistant messages, in `tests/test_escalation.py` (FR-10, SC-006)

### Implementation for User Story 3

- [ ] T033 [US3] Define `EscalationRequest` (reason literal, summary, basket snapshot) in `shopdesk/escalation.py` (FR-10)
- [ ] T034 [US3] Implement the handoff with `input_type=EscalationRequest` and `input_filter=handoff_filters.remove_all_tools` in `shopdesk/escalation.py` (FR-10)
- [ ] T035 [US3] Route all five triggers (not in catalogue, out of stock, ceiling, requested human, unhappy customer) into the typed handoff from `shopdesk/runner.py` (FR-10)
- [ ] T036 [US3] Add the `escalation` check to `scripts/demo_checks.py` printing the typed reason and the before/after history (FR-10, SC-006)

**Checkpoint**: all three conversational stories work independently.

---

## Phase 6: User Story 4 — A long, affordable conversation (Priority: P4)

**Goal**: ten-plus turns in a browser with per-session memory, a cost line from real usage, and one trace per conversation.

**Independent Test**: eleven turns in one Chainlit window, a second window with its own basket, then read the cost line and the trace.

### Implementation for User Story 4

- [ ] T037 [P] [US4] Implement the run-level cost line in `shopdesk/hooks.py`: per-turn model, token usage and `fast_path`/`reasoning` tagging from the live run context (FR-11, SC-007)
- [ ] T038 [P] [US4] Implement `PricingAgentHooks` in `shopdesk/hooks.py` and attach it to the pricing clone only (FR-11)
- [ ] T039 [US4] Implement `CostTrackingRunner(Runner)` in `shopdesk/hooks.py`, appending each run's model and token count to `costs.jsonl` (FR-11)
- [ ] T040 [US4] Implement one-trace-per-conversation in `shopdesk/tracing.py` and call it from `shopdesk/runner.py` with `group_id=session_id` (FR-13)
- [ ] T041 [US4] Implement `chainlit_app.py`: per-session `ShopContext` and history in `cl.user_session`, so two windows never share a basket (FR-12)
- [ ] T042 [US4] Implement the trim rule in `chainlit_app.py`: keep the first user message plus the most recent six exchanges, dropping tool-call items first (FR-12)
- [ ] T043 [US4] Add the eleven-turn recall and two-window checks to `scripts/demo_checks.py` (FR-12, SC-005)
- [ ] T044 [US4] Update `specs/001-shop-desk/quickstart.md` with the final cost-line and trace reading steps (SC-007)

**Checkpoint**: all four stories independently demonstrable.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T045 [P] Audit the codebase for stray model literals outside the three sanctioned places — `.env`, the order agent, the re-quote `RunConfig` (FR-1, NFR-2)
- [ ] T046 [P] Verify no prompt string contains `customer_id` and no tool schema contains a context parameter, via a scripted grep check in `scripts/demo_checks.py` (FR-2)
- [ ] T047 Run the full Definition-of-Done sweep from `specs/001-shop-desk/quickstart.md` and record the evidence for each SC in `specs/001-shop-desk/checklists/dod.md` (SC-001…SC-008)
- [ ] T048 [P] Validate `quickstart.md` end to end on a clean checkout: install, configure, run both entry points (SC-007)
- [ ] T049 Confirm `git log` shows the specification artifacts before the first source commit (NFR-5, SC-008)
- [ ] T050 [P] Update `CLAUDE.md` runtime guidance with the demo flags and the three configuration levels (NFR-2)
- [ ] T051 [P] Add the FR-9 clone-identity test: assert shared attributes match by `is`, owned attributes do not, and neither clone declares a model, in `tests/test_clones.py` (FR-9, NFR-2)
- [ ] T052 [P] Add `shopdesk/messages.py` with the canonical sentences from `contracts/handoff-and-guardrail.md` and use them on the guardrail, out-of-stock, ceiling and escalation paths (FR-6, FR-8, FR-10)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup; **blocks all user stories**
- **US1 (Phase 3)**: depends on Foundational — no dependency on other stories
- **US2 (Phase 4)**: depends on Foundational; uses the Desk agent from US1 at runtime but is independently testable through the order agent and tools
- **US3 (Phase 5)**: depends on Foundational; the ceiling trigger from T028 makes one of its five triggers reachable
- **US4 (Phase 6)**: depends on Foundational; its cost line and tracing observe US1's fast path and US2's specialist runs
- **Polish (Phase 7)**: after all desired stories

### Within Each Story

- Tests before implementation; models before services; the guardrail and ceiling catch before the demo checks that rely on them.

### Parallel Opportunities

- Phase 1: T002, T003, T004 in parallel
- Phase 2: T006, T007, T008 in parallel; T005, T009, T010, T011 touch distinct files and can follow
- US1: T012 and T013 in parallel
- US2: T020, T021, T022 in parallel
- US3: T031 and T032 in parallel
- US4: T037 and T038 in parallel
- Polish: T045, T046, T048, T050 in parallel

---

## Parallel Example: User Story 2

```bash
# Tests first, all in parallel:
Task: "Test planted total mismatch in tests/test_orders.py"
Task: "Test guardrail pass/trip in tests/test_guardrails.py"
Task: "Test tool visibility by tier in tests/test_tool_visibility.py"

# Then the independent implementation slices:
Task: "Order agent with model override in shopdesk/agents.py"
Task: "Output guardrail in shopdesk/guardrails.py"
Task: "Tier-gated and disabled tools in shopdesk/tools.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational)
2. Complete Phase 3 (US1)
3. **STOP and validate**: one model call for a price question, correct hours-aware promise, no
   invented price — this alone is the project's thesis

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → demonstrate the fast path (MVP)
3. US2 → demonstrate typed orders, the guardrail and tier-dependent tools
4. US3 → demonstrate typed escalation with trimmed history
5. US4 → demonstrate the ten-turn session, the cost line and the single trace
6. Polish → run the full Definition-of-Done sweep

### Cut Order (when time is short)

FR-11 → FR-9 → the agent-level hooks inside FR-11. Never cut FR-3 (fast path) or FR-6
(catalogue guardrail).

---

## Notes

- [P] tasks touch different files and have no incomplete dependency
- Commit after each task or logical group; every commit message names the FR it advances
- **Source commits MUST come after the four specification artifacts** (NFR-5) — verify with
  `git log` before the first code commit
- Stop at any checkpoint to validate a story independently
