"""The per-turn facade: one place that wires context, hooks, the ceiling and tracing (FR-3, FR-8, FR-11, FR-13).

`ShopDeskRunner` owns a conversation: it injects the catalogue the run must obey, runs the Desk
through the cost-tracking runner under the conversation's trace and turn ceiling, tags fast-path
turns for the cost line, validates a structured order in Python, and converts every failure into
a sentence the customer can read (NFR-4).
"""

from __future__ import annotations

from typing import Any

from agents import RunContextWrapper

from shopdesk import escalation, guardrails, hooks, instructions, pricing, tools, tracing
from shopdesk.agents import desk_agent
from shopdesk.catalogue import Catalogue
from shopdesk.config import Settings
from shopdesk.context import ShopContext
from shopdesk.fastpath import FAST_PATH_TOOL_NAME
from shopdesk.messages import ESCALATION_ACK, GUARDRAIL_REFUSAL, TOOL_FAILURE, TURN_CEILING
from shopdesk.orders import Order, compare_total

try:  # the SDK exposes these from different modules across versions
    from agents.exceptions import MaxTurnsExceeded, OutputGuardrailTripwireTriggered
except ImportError:  # pragma: no cover - fallback for other SDK layouts
    from agents import MaxTurnsExceeded  # type: ignore[attr-defined]

    class OutputGuardrailTripwireTriggered(Exception):  # type: ignore[no-redef]
        """Fallback type when the installed SDK does not export the tripwire exception."""


KEEP_EXCHANGES = 6


class ShopDeskRunner:
    """One conversation with the Desk: carry history, run turns, own the cost line."""

    def __init__(self, settings: Settings, catalogue: Catalogue, context: ShopContext) -> None:
        self.settings = settings
        self.catalogue = catalogue
        self.context = context
        self.escalations: list[escalation.EscalationRequest] = []
        self._history: list[Any] = []

        tools.set_catalogue(catalogue)
        guardrails.set_catalogue(catalogue)
        pricing.set_catalogue(catalogue)
        instructions.set_settings(settings)
        tracing.configure_tracing(settings)
        hooks.COST_HOOKS.session_id = context.session_id

    @property
    def history(self) -> list[Any]:
        """The SDK item list carried between turns (FR-12)."""
        return list(self._history)

    @history.setter
    def history(self, value: list[Any]) -> None:
        self._history = list(value)

    def resolve_prompt(self) -> str:
        """The instructions resolved for this turn, printable before any model call (FR-4)."""
        return instructions.resolve_prompt(self.context, self.settings)

    def cost_line(self) -> str:
        """Turns, tokens and serving models for this conversation (FR-11)."""
        return hooks.COST_HOOKS.cost_line(self.context.session_id)

    def trim_history(self, items: list[Any], keep_exchanges: int = KEEP_EXCHANGES) -> list[Any]:
        """Keep the first user message and the most recent exchanges, tool items first (FR-12)."""
        cleaned = escalation.filter_history(list(items))
        keep = keep_exchanges * 2
        if len(cleaned) <= keep + 1:
            return cleaned
        return [cleaned[0], *cleaned[-keep:]]

    async def run_turn(self, message: str) -> str:
        """Run one customer turn. Never raises: every failure becomes a sentence (NFR-4)."""
        session = self.context.session_id
        hooks.COST_HOOKS.clear_fast_path(session)
        turn_index = self.context.turns + 1

        try:
            with tracing.conversation_trace(session):
                with tracing.conversation_span(session, turn_index):
                    result = await hooks.CostTrackingRunner.run(
                        desk_agent,
                        input=[*self._history, {"role": "user", "content": message}],
                        context=self.context,
                        hooks=hooks.COST_HOOKS,
                        max_turns=self.settings.turn_ceiling,
                    )
        except MaxTurnsExceeded:
            self.context.turns = turn_index
            self._record_escalation("turn_ceiling", message[:200])
            return TURN_CEILING
        except OutputGuardrailTripwireTriggered:
            self.context.turns = turn_index
            return GUARDRAIL_REFUSAL
        except Exception:
            self.context.turns = turn_index
            return TOOL_FAILURE

        self.context.turns = turn_index
        self._history = list(result.to_input_list())
        self._collect_typed_escalations(result)
        if _used_fast_path(result):
            hooks.COST_HOOKS.mark_fast_path(session)
        return self._render_output(result)

    def _render_output(self, result: Any) -> str:
        """Turn the run's final output into the customer-facing sentence (FR-5)."""
        final = getattr(result, "final_output", None)
        if isinstance(final, Order):
            matches, recomputed = compare_total(final)
            sentence = (
                f"Order {final.order_id} is confirmed: {len(final.items)} line(s), "
                f"total {recomputed:g} {self.context.currency}."
            )
            if not matches:
                sentence += (
                    f" The stated total {final.total:g} did not match the recomputed total "
                    f"{recomputed:g}, so I am reporting the recomputed figure."
                )
            return sentence
        text = final if isinstance(final, str) else str(final)
        return text.strip() or ESCALATION_ACK

    def _context_wrapper(self) -> RunContextWrapper[ShopContext]:
        return RunContextWrapper(context=self.context)

    def _record_escalation(self, reason: str, summary: str) -> None:
        try:
            request = escalation.EscalationRequest.from_context(
                reason, summary, self.context  # type: ignore[arg-type]
            )
        except Exception:
            return
        self.escalations.append(request)
        self.context.escalated = True

    def _collect_typed_escalations(self, result: Any) -> None:
        """Keep the typed reason of any handoff that happened during the run (FR-10)."""
        for item in getattr(result, "new_items", None) or []:
            if "HandoffCall" not in type(item).__name__:
                continue
            raw = getattr(item, "arguments", None)
            if not isinstance(raw, str):
                continue
            try:
                request = escalation.EscalationRequest.model_validate_json(raw)
            except Exception:
                continue
            self.escalations.append(request)
            self.context.escalated = True


def _used_fast_path(result: Any) -> bool:
    """True when the run ended on the price tool's own output (FR-3).

    The Desk's tool-use behaviour ends the run on that tool, so the presence of the call in the
    completed run means the answer was the tool's output rather than a model sentence.
    """
    for item in getattr(result, "new_items", None) or []:
        if "ToolCall" not in type(item).__name__:
            continue
        raw = getattr(item, "raw_item", item)
        name = getattr(raw, "name", None) or getattr(item, "name", None)
        if isinstance(name, str) and name.strip() == FAST_PATH_TOOL_NAME:
            return True
    return False
