# Contract: Cost Line, Custom Runner and Tracing

## Run-level hooks — the cost line (FR-11)

```python
class CostLineHooks(RunHooks):
    # on_agent_start / on_agent_end / on_llm_end receive the run context: the numbers come
    # from live usage, never from an estimate
```

- **Accumulates per turn**: `turn_index`, `model` (the model that actually served it), token
  usage, and `path ∈ {"fast_path", "reasoning"}` — `fast_path` when the turn ended on the
  catalogue tool's output (FR-3), otherwise `reasoning`.
- **Prints at conversation end** a line of the form:
  `cost: 7 turns, 6 fast-path, 1 reasoning, 12,480 in / 1,930 out tokens, models: gpt-5-nano x6, gpt-5-mini x1`.
- **Contract**: the line must distinguish fast-path turns from reasoning turns, and every
  number must be attributable to a run — no interpolation, no character-count estimates.

## Agent-level hooks — pricing specialist only (FR-11)

```python
class PricingAgentHooks(AgentHooks): ...
pricing = base_specialist.clone(instructions=..., model_settings=..., hooks=PricingAgentHooks())
```

- Attached to the pricing clone and to no other agent; demonstrates that agent-level hooks are
  a distinct control from run-level hooks.

## Custom runner — per-run ledger (FR-11)

```python
class CostTrackingRunner(Runner):
    # records model + token count per run, appending to costs.jsonl
```

- **Record shape**: `{"session_id", "run_id", "agent", "model", "input_tokens",
  "output_tokens", "turns", "path", "ts"}`.
- **Contract**: records nested specialist runs as well as Desk turns, so the most expensive
  turn of a conversation can be named (FR-13). `costs.jsonl` is gitignored.

## Tracing (FR-13)

- Tracing is on by default, using the key from `.env`; the key may be overridden for export
  only (never printed).
- **One conversation, one trace**: each session wraps all of its turns in a single
  `trace(workflow_name="shop-desk", group_id=<session_id>)`, so the fast-path turns,
  reasoning turns, and nested specialist runs appear together.
- **Reviewable claim**: opening that trace lets a reviewer point at the fast-path turn (one
  model call, tool output as the answer) and name the most expensive turn from the recorded
  usage.

## Turn ceiling interaction (FR-8)

`max_turns=10` is passed on every run. `MaxTurnsExceeded` is caught in `runner.py`, recorded
on the cost line, and converted into an `EscalationRequest(reason="turn_ceiling")` handoff, so
the customer sees a polite sentence rather than an error.
