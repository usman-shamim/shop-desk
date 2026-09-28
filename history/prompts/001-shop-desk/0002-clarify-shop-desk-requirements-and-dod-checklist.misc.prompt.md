---
id: 0002
title: clarify shop desk requirements and dod checklist
stage: misc
date: 2026-09-28
surface: command-code-cli
model: unspecified
feature: 001-shop-desk
branch: 001-shop-desk
user: usman
command: /sp.clarify + /sp.checklist
labels: [clarify, checklist, shop-desk, requirements-quality]
links:
  spec: specs/001-shop-desk/spec.md
  ticket: none
  adr: none
  pr: none
files:
  - specs/001-shop-desk/spec.md
  - specs/001-shop-desk/checklists/dod.md
tests: []
---

## Prompt

/sp.clarify and /sp.checklist for 001-shop-desk: resolve the remaining open decisions (turn ceiling, history-trimming rule, which agent carries the agent-level model override) and generate the requirements-quality checklist that validates the Definition of Done before planning.

## Response snapshot

Ran the clarification scan and put three high-impact questions to the owner; all three were
answered and encoded in `specs/001-shop-desk/spec.md`:

- Turn ceiling = **10 turns** per conversation (FR-8).
- History trimming = keep the **first user message and the most recent 6 exchanges**, discarding
  tool-call items first (FR-12).
- The agent-level model override belongs to a **dedicated order agent**, so the Desk itself stays
  on the process default (FR-1).

Added a `## Clarifications / ### Session 2026-09-28` section with one bullet per answer, and
applied each answer to the requirement it changes. Then generated the Definition-of-Done
requirements-quality checklist at `specs/001-shop-desk/checklists/dod.md` (39 items, CHK001–CHK039
across completeness, clarity, consistency, acceptance criteria, scenario coverage, edge cases,
non-functional requirements, dependencies and ambiguities). The checklist exposed four genuine
requirement gaps, which were closed in the spec the same session: a closed set of escalation
reasons (FR-10), quantities beyond stock (FR-5), mid-conversation catalogue removal plus
read-time stock with no implied reservation (FR-6), and a malformed/missing catalogue at startup
(NFR-4).

## Outcome

- ✅ Impact: Phase 0 artifact 2 hardened; every open decision now has a recorded answer, and the requirement gaps the checklist found were closed rather than deferred.
- 🧪 Tests: none (specification artifacts)
- 📁 Files: specs/001-shop-desk/spec.md, specs/001-shop-desk/checklists/dod.md
- 🔁 Next prompts: /sp.plan with the technology context (OpenAI Agents SDK, process default model, overrides, data model, contracts), then /sp.adr for the two architectural decisions
- 🧠 Reflection: Writing the checklist as questions about the requirements — not about the code — is what surfaced the missing escalation-reason set and the stock-reservation ambiguity.

## Evaluation notes (flywheel)

- Failure modes observed: the checklist's own gaps could have been ignored; closing them in the spec in the same pass kept the artifacts consistent.
- Graders run and results (PASS/FAIL): not run (requirements-quality review only)
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
