<!--
Sync Impact Report
==================
Version change: 1.0.0 (template) → 1.0.0 (ratified, initial adoption) → 1.0.1 (clarification)
Modified principles: none (all template placeholders replaced with initial principles)
Added sections: Core Principles (I–VII), Additional Constraints, Development Workflow & Quality Gates, Governance
Removed sections: none
Amendment 1.0.1 (2026-09-28): Principle II clarified — an agent either declares its own model
or is documented as deliberately inheriting the process default, and a clone MUST NOT restate
an inherited setting. Resolves the NFR-2 / FR-9 reading conflict found by /sp.analyze.
Bump type PATCH: clarification of existing intent; no principle removed or redefined.
Templates requiring updates:
  ✅ .specify/templates/plan-template.md — "Constitution Check" gate is generic; no edit required
  ✅ .specify/templates/spec-template.md — mandatory sections (user scenarios, requirements, success criteria) align
  ✅ .specify/templates/tasks-template.md — task categories align (setup, foundational, per-story, polish)
  ⚠ .commandcode/commands/sp.*.md — no outdated agent-specific references found; no edit required
Follow-up TODOs: none (ratification date set to first adoption, 2026-09-28)
-->

# Shop Desk Constitution

## Core Principles

### I. Specification Before Implementation (NON-NEGOTIABLE)

No source file may be created until the Phase 0 artifacts exist and are committed:
`constitution.md` (this file), `spec.md`, `plan.md`, and `tasks.md`. A single commit
holding both a specification change and an implementation fails this principle even if
the code runs. `git log` is the evidence.

**Rationale**: the specification is the contract the build is graded against; a spec
written after the code is a description, not a constraint.

### II. Cheap Model by Default, Overrides Justified

The process default model is **`gpt-5-nano`**, set **globally** through
`OPENAI_DEFAULT_MODEL` in `.env` (loaded with `python-dotenv`). Exactly two overrides are
permitted, both to **`gpt-5-mini`**, and each MUST be justified in `plan.md`:

1. **Agent level** — the order-reasoning agent (`Agent(model="gpt-5-mini")`), because
   assembling a typed order from a multi-turn conversation requires reasoning beyond a
   catalogue lookup.
2. **Run level** — the single re-quote run (`RunConfig(model="gpt-5-mini")`), which is
   scoped to one run and MUST NOT change any other run's model.

Every agent's model configuration MUST be explicit and justified: an agent either declares its
own model or is documented in `plan.md` as deliberately inheriting the process default, and a
clone MUST NOT restate a setting it inherits (NFR-2, FR-9). Settings that are not inherited,
such as reasoning effort, MUST be declared per agent. Removing the global default MUST change
exactly one behaviour: the model that answers a plain question.

**Rationale**: a price question must never cost a reasoning model; the budget is spent
deliberately, not by accident.

### III. The Catalogue Is the Only Source of Truth

No price, stock figure, catalogue identifier, or SKU MAY reach a customer unless it was
read from `catalogue.json` during that run. Products are reachable only through tools. An
output guardrail MUST compare the finished answer against the catalogue file and refuse
an answer that quotes a price or SKU not present in it. This is a data check, not a
judgement call. An out-of-stock item MUST NOT be sold.

**Rationale**: the failure this project exists to prevent is a confident, invented price.

### IV. Secrets Live Only in `.env`

API keys and credentials MUST live in `.env`, which MUST be gitignored, and MUST NEVER be
printed to a prompt, a log, a trace, or a commit. A missing key MUST fail at startup with
a single readable sentence, never a stack trace (NFR-1).

**Rationale**: a leaked key is a cost incident, and an unreadable startup failure is a
support incident.

### V. Tools Return Sentences, Never Exceptions

No tool may raise into the runner. A tool meeting bad data or an impossible request MUST
return a short sentence the model can use and act on. A tool that raises is a defect, not
an edge case (NFR-4).

**Rationale**: the runner is a conversation; an exception ends the conversation for a
condition the customer could have been told about in one line.

### VI. Typed Boundaries, Numbers Recomputed

Anything crossing a boundary between the customer, the model, a specialist, or a human
MUST be a typed structure, not prose: a confirmed order is a typed object, an escalation
carries a typed reason, and shop context is a typed object that never appears in prompt
text. Monetary totals MUST be recomputed in Python from the typed line items, and a
discrepancy between the model's figure and the recomputed figure MUST be reported rather
than silently accepted.

**Rationale**: prose cannot be validated, and a total taken on trust is an unverified
invoice.

### VII. Facts Take the Fast Path

A question answerable from the catalogue alone MUST be answerable in exactly one model
call: the lookup tool's own output is the customer-facing answer, and the model neither
sees the result nor writes a sentence around it. Ordinary questions keep the normal
reasoning loop.

**Rationale**: the project's theme is not wasting money — the cheapest correct answer is
the one no model has to phrase.

## Additional Constraints

- **Stack**: Python 3.11+, OpenAI Agents SDK (`openai-agents`), `pydantic` for typed
  boundaries, `python-dotenv` for configuration, Chainlit for the conversation interface.
- **Requirements are numbered and testable**: every capability is an `FR-n` and every
  constraint an `NFR-n`; "FR-3 works" MUST be demonstrable on demand.
- **Conversation lifecycle**: every conversation runs under a turn ceiling that raises,
  is caught, and ends politely; a whole customer conversation is one trace; history
  carried into a handoff or a long session is trimmed by a stated, justified rule.
- **Cost accounting**: each conversation MUST report turns, tokens, and the model that
  served each turn, sourced from run context, not estimated.

## Development Workflow & Quality Gates

1. **Specify → Plan → Tasks → Implement.** Work proceeds in that order through the Spec
   Kit Plus commands; each artifact is committed before the next begins.
2. **Traceability**: every task in `tasks.md` names the requirement it serves; every
   architectural decision of consequence is recorded as an ADR.
3. **Cross-artifact gate**: `/sp.analyze` MUST report consistency across constitution,
   specification, plan, and tasks before implementation starts.
4. **Verification over assertion**: a requirement is complete when its check in the
   specification's Definition of Done has been executed and observed, not when the code
   has been written.
5. **Cut order** (when time is short): FR-11, then FR-9, then the agent-level hooks inside
   FR-11. The fast path (FR-3) and the catalogue guardrail (FR-6) are never cut.

## Governance

This constitution supersedes other practices where they conflict. Amendments are made by
updating this file through the `/sp.constitution` command and MUST include: the version
bump, the rationale, and a Sync Impact Report covering every dependent artifact.
Versioning follows semantic versioning — MAJOR for incompatible governance or principle
removals/redefinitions, MINOR for a new or materially expanded principle, PATCH for
clarifications and non-semantic refinements.

Compliance is reviewed at each phase gate listed in the specification's Definition of
Done. Any complexity that conflicts with a principle MUST be recorded in `plan.md` under
Complexity Tracking with the simpler alternative that was rejected and why. Runtime
development guidance lives in `CLAUDE.md`.

**Version**: 1.0.1 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-09-28
