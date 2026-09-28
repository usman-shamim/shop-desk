"""Run-level cost tracking, pricing agent hooks and the ledger-writing runner (FR-11).

Every figure here is read from the live run — the agent that served a call and the model
response's own usage — never estimated. ``CostLineHooks`` appends one ``TurnRecord`` per model
call and renders the per-conversation cost line, distinguishing fast-path turns (the turn ended
on the catalogue tool's output, FR-3) from reasoning turns. ``PricingAgentHooks`` counts runs of
the pricing specialist alone. ``CostTrackingRunner`` appends one JSON line per run to
``costs.jsonl`` so the most expensive turn of a conversation can be named (FR-13).
"""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from agents import (
    Agent,
    AgentHookContext,
    AgentHooks,
    RunConfig,
    RunContextWrapper,
    RunHooks,
    Runner,
)
from agents.items import ModelResponse
from agents.models.default_models import get_default_model
from agents.result import RunResult, RunResultStreaming

PathKind = Literal["fast_path", "reasoning"]

LEDGER_ENV_VAR = "COST_LEDGER_PATH"
DEFAULT_LEDGER_NAME = "costs.jsonl"

_PRICING_RUN_COUNT = 0


@dataclass
class TurnRecord:
    """One model call, read from the live run (FR-11)."""

    turn_index: int
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    path: PathKind
    session_id: str


def _model_name(candidate: Any) -> str | None:
    """The model name behind a ``str`` or a ``Model`` instance, if one is declared."""
    if isinstance(candidate, str):
        return candidate or None
    declared = getattr(candidate, "model", None)
    if isinstance(declared, str):
        return declared or None
    return None


def _run_config_model(run_config: Any) -> Any:
    if run_config is None:
        return None
    if isinstance(run_config, dict):
        return run_config.get("model")
    return getattr(run_config, "model", None)


def _run_config_group(run_config: Any) -> str | None:
    if run_config is None:
        return None
    value = run_config.get("group_id") if isinstance(run_config, dict) else getattr(
        run_config, "group_id", None
    )
    return value if isinstance(value, str) and value else None


def _agent_name(agent: Any) -> str | None:
    name = getattr(agent, "name", None)
    return name if isinstance(name, str) and name else None


def _usage_counts(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    return (
        int(getattr(usage, "input_tokens", 0) or 0),
        int(getattr(usage, "output_tokens", 0) or 0),
    )


def _session_id_of(context: Any, fallback: str) -> str:
    shop_context = getattr(context, "context", None)
    session_id = getattr(shop_context, "session_id", None)
    if isinstance(session_id, str) and session_id:
        return session_id
    return fallback


def resolve_model_name(agent: Any, run_config: RunConfig | dict[str, Any] | None = None) -> str:
    """The model that actually served the run, read from the run rather than estimated (FR-11)."""
    from_config = _model_name(_run_config_model(run_config))
    if from_config:
        return from_config
    declared = _model_name(getattr(agent, "model", None))
    if declared:
        return declared
    return get_default_model()


def ledger_path() -> Path:
    """``costs.jsonl`` in the project root, or ``COST_LEDGER_PATH`` when set (FR-11)."""
    override = os.getenv(LEDGER_ENV_VAR)
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / DEFAULT_LEDGER_NAME


def _append_ledger(record: dict[str, Any]) -> None:
    try:
        path = ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        return


class CostLineHooks(RunHooks):
    """Per-conversation cost line built from run-level lifecycle events (FR-11)."""

    def __init__(self) -> None:
        self.session_id: str = "local"
        self.model_override: str | None = None
        self._records: dict[str, list[TurnRecord]] = {}
        self._fast_path: dict[str, bool] = {}
        self._current_agent: dict[str, str] = {}

    async def on_agent_start(self, context: AgentHookContext[Any], agent: Agent[Any]) -> None:
        session_id = _session_id_of(context, self.session_id)
        self._current_agent[session_id] = _agent_name(agent) or "unknown-agent"

    async def on_llm_end(
        self, context: RunContextWrapper[Any], agent: Agent[Any], response: ModelResponse
    ) -> None:
        session_id = _session_id_of(context, self.session_id)
        input_tokens, output_tokens = _usage_counts(response)
        records = self._records.setdefault(session_id, [])
        records.append(
            TurnRecord(
                turn_index=len(records) + 1,
                agent=_agent_name(agent) or self._current_agent.get(session_id, "unknown-agent"),
                model=self._resolve_model(agent),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                path="fast_path" if self._fast_path.get(session_id) else "reasoning",
                session_id=session_id,
            )
        )

    async def on_agent_end(
        self, context: AgentHookContext[Any], agent: Agent[Any], output: Any
    ) -> None:
        session_id = _session_id_of(context, self.session_id)
        self._current_agent.pop(session_id, None)

    def _resolve_model(self, agent: Any) -> str:
        if self.model_override:
            return self.model_override
        return resolve_model_name(agent)

    def mark_fast_path(self, session_id: str) -> None:
        """Tag the current turn of ``session_id`` as a fast-path turn (FR-3, FR-11)."""
        self._fast_path[session_id] = True
        records = self._records.get(session_id)
        if records and records[-1].path != "fast_path":
            records[-1] = replace(records[-1], path="fast_path")

    def clear_fast_path(self, session_id: str) -> None:
        """Forget the fast-path flag for ``session_id`` so the next turn starts as reasoning."""
        self._fast_path.pop(session_id, None)

    def last_path_was_fast_path(self, session_id: str) -> bool:
        """Whether the most recent turn of ``session_id`` ended on the fast path (FR-3)."""
        records = self._records.get(session_id)
        if records:
            return records[-1].path == "fast_path"
        return bool(self._fast_path.get(session_id))

    def records(self, session_id: str) -> list[TurnRecord]:
        """The turns recorded for one conversation, in order (FR-11)."""
        return list(self._records.get(session_id, []))

    def all_records(self) -> list[TurnRecord]:
        """Every recorded turn across all conversations (FR-11)."""
        return [record for records in self._records.values() for record in records]

    def cost_line(self, session_id: str | None = None) -> str:
        """The per-conversation cost line, distinguishing fast-path from reasoning turns (FR-11)."""
        session = session_id or self.session_id
        records = self._records.get(session, [])
        turns = len(records)
        fast = sum(1 for record in records if record.path == "fast_path")
        reasoning = turns - fast
        input_tokens = sum(record.input_tokens for record in records)
        output_tokens = sum(record.output_tokens for record in records)
        return (
            f"cost: {turns} turns, {fast} fast-path, {reasoning} reasoning, "
            f"{input_tokens} in / {output_tokens} out tokens, "
            f"models: {self._model_summary(records)}"
        )

    @staticmethod
    def _model_summary(records: list[TurnRecord]) -> str:
        if not records:
            return "none"
        counts = Counter(record.model for record in records)
        return ", ".join(f"{model} x{count}" for model, count in counts.items())


class PricingAgentHooks(AgentHooks):
    """Agent-level hooks attached to the pricing specialist only (FR-11)."""

    async def on_start(self, context: AgentHookContext[Any], agent: Agent[Any]) -> None:
        global _PRICING_RUN_COUNT
        _PRICING_RUN_COUNT += 1


def pricing_runs() -> int:
    """Number of pricing-specialist runs counted by ``PricingAgentHooks`` (FR-11)."""
    return _PRICING_RUN_COUNT


def _result_agent(result: Any) -> Any:
    try:
        return result.last_agent
    except Exception:
        return None


def _run_usage(result: Any) -> tuple[int, int]:
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
    if usage is not None:
        return (
            int(getattr(usage, "input_tokens", 0) or 0),
            int(getattr(usage, "output_tokens", 0) or 0),
        )
    input_tokens = 0
    output_tokens = 0
    for response in getattr(result, "raw_responses", []) or []:
        counted_in, counted_out = _usage_counts(response)
        input_tokens += counted_in
        output_tokens += counted_out
    return input_tokens, output_tokens


def _ended_on_tool_output(result: Any) -> bool:
    final_output = getattr(result, "final_output", None)
    for item in getattr(result, "new_items", []) or []:
        if getattr(item, "type", None) == "tool_call_output_item":
            if getattr(item, "output", None) == final_output:
                return True
    return False


def _run_id(result: Any) -> str:
    response_id = getattr(result, "last_response_id", None)
    if isinstance(response_id, str) and response_id:
        return response_id
    return uuid4().hex


def _session_id_for(result: Any, run_config: Any) -> str:
    shop_context = getattr(getattr(result, "context_wrapper", None), "context", None)
    session_id = getattr(shop_context, "session_id", None)
    if isinstance(session_id, str) and session_id:
        return session_id
    return _run_config_group(run_config) or COST_HOOKS.session_id


def record_run(result: Any, starting_agent: Any, run_config: Any = None) -> None:
    """Append one ledger line for a finished run; a ledger failure never breaks the run (FR-11)."""
    agent = _result_agent(result) or starting_agent
    session_id = _session_id_for(result, run_config)
    if COST_HOOKS.last_path_was_fast_path(session_id) or _ended_on_tool_output(result):
        path: PathKind = "fast_path"
    else:
        path = "reasoning"
    input_tokens, output_tokens = _run_usage(result)
    _append_ledger(
        {
            "session_id": session_id,
            "run_id": _run_id(result),
            "agent": _agent_name(agent) or "unknown-agent",
            "model": resolve_model_name(agent, run_config),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "turns": len(getattr(result, "raw_responses", []) or []),
            "path": path,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )


def _starting_agent(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    if args:
        return args[0]
    return kwargs.get("starting_agent")


def _run_config_from(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    if "run_config" in kwargs:
        return kwargs["run_config"]
    if len(args) > 5:
        return args[5]
    return None


def _set_model_override(run_config: Any) -> None:
    COST_HOOKS.model_override = _model_name(_run_config_model(run_config))


class CostTrackingRunner(Runner):
    """A ``Runner`` that records each run's model and token count in ``costs.jsonl`` (FR-11)."""

    @classmethod
    async def run(cls, *args: Any, **kwargs: Any) -> RunResult:
        _set_model_override(_run_config_from(args, kwargs))
        try:
            result = await super().run(*args, **kwargs)
        finally:
            COST_HOOKS.model_override = None
        record_run(result, _starting_agent(args, kwargs), _run_config_from(args, kwargs))
        return result

    @classmethod
    def run_sync(cls, *args: Any, **kwargs: Any) -> RunResult:
        _set_model_override(_run_config_from(args, kwargs))
        try:
            result = super().run_sync(*args, **kwargs)
        finally:
            COST_HOOKS.model_override = None
        record_run(result, _starting_agent(args, kwargs), _run_config_from(args, kwargs))
        return result

    @classmethod
    def run_streamed(cls, *args: Any, **kwargs: Any) -> RunResultStreaming:
        _set_model_override(_run_config_from(args, kwargs))
        try:
            result = super().run_streamed(*args, **kwargs)
        finally:
            COST_HOOKS.model_override = None
        record_run(result, _starting_agent(args, kwargs), _run_config_from(args, kwargs))
        return result


COST_HOOKS = CostLineHooks()
PRICING_HOOKS = PricingAgentHooks()
