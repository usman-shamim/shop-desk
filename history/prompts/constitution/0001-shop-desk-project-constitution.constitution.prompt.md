---
id: 0001
title: shop-desk project constitution
stage: constitution
date: 2026-09-28
surface: command-code-cli
model: unspecified
feature: none
branch: master
user: usman
command: /sp.constitution
labels: [constitution, governance, shop-desk]
links:
  spec: none
  ticket: none
  adr: none
  pr: none
files:
  - .specify/memory/constitution.md
tests: []
---

## Prompt

/sp.constitution Create the governing principles for Shop Desk: the cheap model is the process default and only named agents may override it; a quoted price must come from the catalogue; secrets live only in .env; no tool raises into the runner. Requirements are numbered and testable, and the specification is committed before any code.

## Response snapshot

Ratified Shop Desk Constitution v1.0.0 in `.specify/memory/constitution.md` with seven principles:
I. Specification Before Implementation (NON-NEGOTIABLE); II. Cheap Model by Default, Overrides
Justified (global `gpt-5-nano` via `OPENAI_DEFAULT_MODEL` in `.env`, two sanctioned `gpt-5-mini`
overrides — order-reasoning agent at agent level, re-quote at run level); III. The Catalogue Is the
Only Source of Truth; IV. Secrets Live Only in `.env`; V. Tools Return Sentences, Never Exceptions;
VI. Typed Boundaries, Numbers Recomputed; VII. Facts Take the Fast Path. Added Additional
Constraints, Development Workflow & Quality Gates (including the cut order), and Governance with
semantic versioning and a Sync Impact Report. All template placeholders replaced; plan/spec/tasks
templates verified as already aligned (no edits required).

## Outcome

- ✅ Impact: Phase 0 artifact 1 of 4 ratified; every later artifact now has a constitution to check against.
- 🧪 Tests: none (documentation artifact)
- 📁 Files: .specify/memory/constitution.md
- 🔁 Next prompts: /sp.specify with the Shop Desk brief and FR-1…FR-13; then /sp.clarify and /sp.checklist
- 🧠 Reflection: Binding the two `gpt-5-mini` overrides to named call sites (agent vs run) makes the cost theme auditable rather than aspirational.

## Evaluation notes (flywheel)

- Failure modes observed: `sp init` initial git commit failed (no git user.email configured); resolved by setting a repository-local identity.
- Graders run and results (PASS/FAIL): not run yet
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
