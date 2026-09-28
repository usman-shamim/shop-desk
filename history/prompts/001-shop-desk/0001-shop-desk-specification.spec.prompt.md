---
id: 0001
title: shop desk specification
stage: spec
date: 2026-09-28
surface: command-code-cli
model: unspecified
feature: 001-shop-desk
branch: 001-shop-desk
user: usman
command: /sp.specify
labels: [spec, shop-desk, requirements]
links:
  spec: specs/001-shop-desk/spec.md
  ticket: none
  adr: none
  pr: none
files:
  - specs/001-shop-desk/spec.md
  - specs/001-shop-desk/checklists/requirements.md
tests: []
---

## Prompt

/sp.specify Shop Desk: a customer-service desk for a small shop that answers stock and price questions from a catalogue, builds a typed order when the customer confirms, and hands genuinely stuck conversations to a human.

## Response snapshot

Created feature branch `001-shop-desk` and wrote `specs/001-shop-desk/spec.md` with four
prioritized user stories (P1 catalogue price answers in one call plus hour-aware promises; P2
typed orders, recomputed totals, catalogue guardrail, tier-dependent tools, pricing specialist
and turn ceiling; P3 escalation with structured reason and filtered history; P4 ten-plus-turn
browser conversation with a cost line and one trace). Recorded FR-1…FR-13 and NFR-1…NFR-5 as
testable behaviour, seven edge cases, six key entities, SC-001…SC-008 as technology-agnostic
measurable outcomes, five assumptions, and the three deliberate non-goals required by the
guide (no order persistence, no bargaining input guardrail, no fast-path cache). Added the
specification quality checklist at `specs/001-shop-desk/checklists/requirements.md`; all items
pass with no [NEEDS CLARIFICATION] markers.

## Outcome

- ✅ Impact: Phase 0 artifact 2 of 4 written; every requirement from the project guide is now traceable to a numbered, testable statement.
- 🧪 Tests: none (specification artifact)
- 📁 Files: specs/001-shop-desk/spec.md, specs/001-shop-desk/checklists/requirements.md
- 🔁 Next prompts: /sp.clarify for the remaining open choices, then /sp.checklist for the Definition-of-Done checklist
- 🧠 Reflection: Keeping model names out of the specification and in the constitution/plan preserved the what-not-how rule while still making FR-1's three configuration levels testable.

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): specification quality checklist — all items PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
