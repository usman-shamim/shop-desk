# Implementation Plan: Shop Desk

**Branch**: `001-shop-desk` | **Date**: 2026-09-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-shop-desk/spec.md`

**Note**: This file is filled in by the `/sp.plan` command.

## Summary

A customer-service Desk for a small shop, built on the **OpenAI Agents SDK** as the only
agent framework. The Desk answers catalogue questions, takes orders as typed objects, and
escalates stuck conversations to a human. The dominant technical constraint is cost: the
process default model is a cheap model, exactly two call sites override it, a catalogue
price question is answered in **one model call** with the model never seeing the tool
result, and every conversation reports what its turns cost.

Technical approach in one line: a **Desk agent** (process-default model) with catalogue
tools and a tool-output fast path, a **dedicated order agent** (`output_type=Order`) that
carries the agent-level model override, a **pricing specialist** and an **escalation
specialist** cloned from one base, an output guardrail that checks the finished answer
against `catalogue.json`, a run-level cost line, and a Chainlit session for the ten-turn
conversation.

## Technical Context

**Language/Version**: Python 3.10+ (SDK requirement); developed and demonstrated on 3.11+
**Primary Dependencies**: `openai-agents` (the only agent framework — agents, tools,
handoffs, guardrails, hooks, sessions, tracing), `python-dotenv` (configuration),
`pydantic` (typed boundaries; already an SDK dependency), `chainlit` (browser interface
for FR-12 only)
**Storage**: `catalogue.json` read at run time (single source of price/stock truth);
`costs.jsonl` append-only run ledger written by the custom runner. No database
**Testing**: `pytest` for total recomputation, guardrail truth checks, tool failure
behaviour and tool visibility by tier; scripted demo checks for the observable claims
(call counts, trimmed history, resolved prompt)
**Target Platform**: Linux local workstation; Chainlit served on localhost
**Project Type**: single project (library package plus two entry points: CLI and Chainlit)
**Performance Goals**: not a latency project — the goal is *calls per answer*: 1 model call
for a catalogue price question, more for an order conversation. A few seconds per
reasoning turn is acceptable
**Constraints**: process default model set globally and overridable only at the two named
call sites; turn ceiling of 10 per conversation; 6-exchange history trim; secrets only in a
gitignored `.env`; no tool may raise into the runner
**Scale/Scope**: one shop, a catalogue of tens of products, one customer per session, four
agents (Desk, order, pricing, escalation), ~8 tools, 13 FRs / 5 NFRs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Specification Before Implementation | This plan, the spec, the constitution and the task list are committed before any source file | **PASS** — `git log` contains only specification artifacts; no source file exists |
| II. Cheap Model by Default, Overrides Justified | Exactly three configuration levels; two overrides, both justified below | **PASS** — overrides at the order agent (agent level) and the re-quote path (run level); global default via `OPENAI_DEFAULT_MODEL` |
| III. Catalogue Is the Only Source of Truth | Products reachable only through tools; output guardrail compares against the file | **PASS** — `tools.py` + `guardrails.py`; no price literal in any prompt |
| IV. Secrets Only in `.env` | Key from `.env` via dotenv, gitignored; startup fails with one sentence | **PASS** — `config.py` validates before any client is created |
| V. Tools Return Sentences, Never Exceptions | Every tool returns a usable sentence on bad data | **PASS** — `failure_error_function` per tool plus in-tool guards; nothing raises into the runner |
| VI. Typed Boundaries, Numbers Recomputed | Order, escalation reason and shop context typed; totals recomputed in Python | **PASS** — `orders.py`, `escalation.py`, `context.py` |
| VII. Facts Take the Fast Path | Catalogue-only answer costs exactly one model call | **PASS** — `fastpath.py` via `tool_use_behavior` |

No gate is violated; Complexity Tracking records the two deliberate additions.

## Project Structure

### Documentation (this feature)

```text
specs/001-shop-desk/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output: SDK mechanism decisions
├── data-model.md        # Phase 1 output: entities and validation rules
├── quickstart.md        # Phase 1 output: how to run and how to check the DoD
├── contracts/           # Phase 1 output: tool, agent, handoff, guardrail, cost contracts
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
shopdesk/
├── __init__.py
├── config.py         # dotenv load; startup validation (NFR-1); hours + simulated clock
├── context.py        # ShopContext dataclass; tier; basket held per session
├── catalogue.py      # catalogue.json load + read-time lookups (NFR-3)
├── orders.py         # LineItem, Order, recompute_total, mismatch report
├── instructions.py   # FR-4 dynamic instruction builder (context + clock)
├── tools.py          # lookup_price, lookup_stock, place_order, seasonal (off), loyalty (regular)
├── fastpath.py       # FR-3 tool_use_behavior: price answer as final output
├── guardrails.py     # FR-6 output guardrail against the catalogue file
├── agents.py         # Desk agent, order agent, base specialist + clones (FR-9)
├── pricing.py        # FR-8 pricing specialist exposed via as_tool
├── escalation.py     # FR-10 handoff, EscalationRequest, history filter
├── hooks.py          # FR-11 RunHooks cost line, pricing AgentHooks, CostTrackingRunner
├── tracing.py        # FR-13 one trace per conversation
└── runner.py         # facade: wires config, context, hooks, ceiling, tracing per turn

main.py                # CLI entry point (REPL + demo flags: --print-prompt, --hour, --tier)
chainlit_app.py        # FR-12 browser session, per-session context, history trim
catalogue.json         # the shop's catalogue (Al-Noor Electronics sample)
.env.example           # documented keys (values never committed)
scripts/demo_checks.py # observable claims: call counts, guardrail trip, trimmed history
tests/
├── test_orders.py
├── test_guardrails.py
├── test_tools.py
└── test_tool_visibility.py
```

**Structure Decision**: single project, package `shopdesk` with one module per
responsibility, so each requirement maps to a file a reviewer can point at — FR-1 to
`config.py`/`agents.py`, FR-3 to `fastpath.py`, FR-6 to `guardrails.py`, FR-11 to
`hooks.py`. Two entry points share one `runner.py` facade: the CLI for demonstrations and
Chainlit for FR-12.

## Model Configuration (FR-1) — the three levels, named

1. **Process / global** — `OPENAI_DEFAULT_MODEL=gpt-5-nano` in `.env`, loaded by
   `python-dotenv` in `config.py` before the first model call. This is the model that
   answers a plain question; deleting this line changes exactly that one behaviour.
2. **Agent** — the dedicated order agent (`agents.py`) declares
   `Agent(name="order_assembler", model="gpt-5-mini", output_type=Order)`. Justification:
   assembling a validated order from a multi-turn conversation and recomputing its total is
   genuine reasoning; a catalogue lookup is not. The Desk, pricing and escalation agents
   declare no model and inherit the process default.
3. **Run** — the re-quote path calls `Runner.run(..., run_config=RunConfig(model="gpt-5-mini"))`
   for that single run only, when a customer asks for a price the Desk cannot derive from
   the catalogue.

**Done-when check**: delete `OPENAI_DEFAULT_MODEL` from `.env`; the Desk, pricing and
escalation agents lose their model, while the order agent is unaffected because it names
its own.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Chainlit as a UI dependency | FR-12 requires a browser conversation of 10+ turns with per-session history; Chainlit is the SDK's documented frontend and provides session state, while the agent side stays pure SDK + dotenv | A hand-rolled `http.server` + SSE page keeps dependencies minimal but is not the SDK's documented path and spends effort better used on the cost-control requirements |
| Two extra modules (`fastpath.py`, `hooks.py`) | FR-3 and FR-11 are the two requirements the project is graded on; isolating each makes it independently demonstrable in review | Folding them into `agents.py`/`runner.py` would make the fast path and the cost line harder to point at |

## Post-Design Constitution Re-check

| Principle | Re-check after Phase 1 design | Status |
|-----------|-------------------------------|--------|
| I | Design artifacts committed; still zero source files | **PASS** |
| II | The model choice appears in exactly three places (`.env`, order agent, re-quote `RunConfig`); every other agent declares none | **PASS** |
| III | Guardrail compares extracted price/SKU tokens against the loaded catalogue; tools are the only catalogue readers | **PASS** |
| IV | `config.py` loads `.env` and exits with one sentence on a missing key; no key is ever printed | **PASS** |
| V | `failure_error_function` on every tool; in-tool guards for unknown SKU and bad quantity | **PASS** |
| VI | `Order`, `EscalationRequest`, `ShopContext` typed; `recompute_total` is the only source of a total | **PASS** |
| VII | Fast path implemented as tool-use behaviour, holding catalogue-only answers at one model call | **PASS** |

## Phase Gates

- **Phase 0 (research)** complete — every SDK mechanism the design depends on has a
  decision and an alternative recorded in `research.md`; no NEEDS CLARIFICATION remains.
- **Phase 1 (design)** complete — `data-model.md`, `contracts/`, `quickstart.md` written and
  agent context updated.
- **Phase 2 (tasks)** is the next command (`/sp.tasks`), not part of this one.
