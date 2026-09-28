---
id: 0003
title: shop desk implementation plan and adrs
stage: plan
date: 2026-09-28
surface: command-code-cli
model: unspecified
feature: 001-shop-desk
branch: 001-shop-desk
user: usman
command: /sp.plan + /sp.adr
labels: [plan, research, data-model, contracts, adr, shop-desk]
links:
  spec: specs/001-shop-desk/spec.md
  ticket: none
  adr: history/adr/0001-three-level-model-configuration-for-cost-control.md, history/adr/0002-tool-output-fast-path-for-catalogue-price-answers.md
  pr: none
files:
  - specs/001-shop-desk/plan.md
  - specs/001-shop-desk/research.md
  - specs/001-shop-desk/data-model.md
  - specs/001-shop-desk/quickstart.md
  - specs/001-shop-desk/contracts/tools.md
  - specs/001-shop-desk/contracts/agents.md
  - specs/001-shop-desk/contracts/handoff-and-guardrail.md
  - specs/001-shop-desk/contracts/cost-and-tracing.md
  - history/adr/0001-three-level-model-configuration-for-cost-control.md
  - history/adr/0002-tool-output-fast-path-for-catalogue-price-answers.md
  - CLAUDE.md
tests: []
---

## Prompt

/sp.plan the Shop Desk using the OpenAI Agents SDK as the only agent framework, python-dotenv for configuration, pydantic for typed boundaries and Chainlit only as the browser shell. Then /sp.adr for the architectural decisions that matter.

## Response snapshot

Wrote the planning set for `001-shop-desk`:

- **plan.md** — summary, technical context (Python 3.10+, `openai-agents`, python-dotenv,
  pydantic, Chainlit for FR-12 only), the constitution check (all seven principles PASS) and
  post-design re-check, the module-per-requirement source layout, the three model-configuration
  levels named with their call sites, Complexity Tracking for the Chainlit dependency and the
  two dedicated modules, and the phase gates.
- **research.md** — 17 decisions (R1–R17), each with rationale and rejected alternatives:
  global/agent/run model levels, context invisibility via `RunContextWrapper`, the tool-output
  fast path, dynamic instructions, structured order plus Python-recomputed total, the
  data-comparison output guardrail, static `is_enabled=False` versus a tier callable, the
  pricing specialist via `as_tool` with a figure-only extractor, the 10-turn ceiling and
  `MaxTurnsExceeded`, `clone()`-based specialists, the typed+filtered handoff, the cost line,
  custom runner, one trace per conversation, and the Chainlit trim rule.
- **data-model.md** — `ShopContext`, `Product`, `LineItem`, `Order` (with state transitions),
  `EscalationRequest`, `CostLine`, `SessionState`, each mapped to the requirement it serves.
- **contracts/** — tools.md (including the fast-path contract and failure sentences),
  agents.md (model ownership per agent, shared-versus-owned clone attributes), handoff-and-
  guardrail.md (typed reason set, exactly what `remove_all_tools` removes), cost-and-tracing.md.
- **quickstart.md** — environment keys, run commands, and a table mapping each
  Definition-of-Done claim to the command or action that shows it.
- **ADRs** — ADR-0001 three-level model configuration for cost control; ADR-0002 the
  tool-output fast path, with its trade-off (the Desk loses its own phrasing of a price) stated
  explicitly.
- Ran `update-agent-context.sh claude`, which added the language/framework/storage lines to
  `CLAUDE.md`.

## Outcome

- ✅ Impact: Phase 0 research and Phase 1 design complete; no NEEDS CLARIFICATION remains and the constitution check passes both before and after design.
- 🧪 Tests: none (planning artifacts)
- 📁 Files: plan.md, research.md, data-model.md, quickstart.md, 4 contract files, 2 ADRs, CLAUDE.md
- 🔁 Next prompts: /sp.tasks to break the plan into ordered, FR-tagged tasks; then /sp.analyze
- 🧠 Reflection: Naming the exact SDK mechanism for each requirement (rather than a technology) is what kept the plan testable — every FR now has a named call site to point at in review.

## Evaluation notes (flywheel)

- Failure modes observed: an earlier draft line in research.md was malformed; corrected before commit. A malformed `plan.md` write was initially rejected because the copied template had not been read in full — read the file before overwriting script-generated artifacts.
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
