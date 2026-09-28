---
id: 0004
title: shop desk task breakdown
stage: tasks
date: 2026-09-28
surface: command-code-cli
model: unspecified
feature: 001-shop-desk
branch: 001-shop-desk
user: usman
command: /sp.tasks
labels: [tasks, shop-desk, traceability]
links:
  spec: specs/001-shop-desk/spec.md
  ticket: none
  adr: history/adr/0001-three-level-model-configuration-for-cost-control.md
  pr: none
files:
  - specs/001-shop-desk/tasks.md
tests: []
---

## Prompt

/sp.tasks for 001-shop-desk: break the plan into ordered, independently verifiable tasks, each naming the requirement it serves, grouped by user story.

## Response snapshot

Generated `specs/001-shop-desk/tasks.md` with 50 tasks in the required checklist format
(`[ID] [P?] [Story] description + file path`), grouped as:

- **Phase 1 Setup** (T001–T004): package skeleton, `.env.example`, sample `catalogue.json`,
  test configuration.
- **Phase 2 Foundational** (T005–T011): config/startup validation, `ShopContext`, catalogue
  loader, `Order`/`LineItem` with `recompute_total`, base specialist plus clones, the runner
  facade, dynamic instructions.
- **Phase 3 US1 (P1, MVP)** (T012–T019): price/stock tools, the fast path, the Desk agent,
  hours-aware promises, the CLI, and the call-count evidence check.
- **Phase 4 US2 (P2)** (T020–T030): order tools, the order agent with the agent-level model
  override, the catalogue guardrail with a polite catch, tier-gated and disabled tools, the
  pricing specialist, the 10-turn ceiling, the run-level re-quote override, and the catalogue-
  edit/mismatch evidence checks.
- **Phase 5 US3 (P3)** (T031–T036): `EscalationRequest`, the typed handoff with
  `remove_all_tools`, all five triggers, and the before/after history check.
- **Phase 6 US4 (P4)** (T037–T044): cost line, pricing-only agent hooks, the cost-tracking
  runner, one trace per conversation, the Chainlit session, the trim rule, the eleven-turn and
  two-window checks.
- **Phase 7 Polish** (T045–T050): model-literal audit, the FR-2 grep check, the full DoD sweep
  recorded in the checklist, quickstart validation, `git log` provenance check, `CLAUDE.md`
  update.

Every task names its requirement, tests are written before implementation in each story, the
cut order from the constitution is repeated, and the dependency graph plus parallel examples
per story are included.

## Outcome

- ✅ Impact: Phase 0 artifact 4 of 4 complete — the four graded spec artifacts now exist and are internally consistent; implementation can begin with a verifiable order of work.
- 🧪 Tests: 8 test tasks specified across stories (written before their implementation tasks)
- 📁 Files: specs/001-shop-desk/tasks.md
- 🔁 Next prompts: /sp.analyze to check cross-artifact consistency before any code
- 🧠 Reflection: Mapping each task to an FR kept the task list honest — anything that could not name a requirement was either dropped or moved into the polish phase as evidence work.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): not run
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
