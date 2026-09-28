"""Escalation handoff: a typed reason plus a tool-free transcript (FR-10, SC-006).

Serves FR-10 by making every escalation travel as an ``EscalationRequest`` carrying one of
the five closed reasons, a one-line summary (<= 200 chars) and a snapshot of the basket, and
by building the handoff with ``input_type=EscalationRequest`` and a history ``input_filter``.
Serves SC-006 by exposing ``filter_history``/``describe_history`` so the demo check can print
the before/after of the transfer with tool activity removed.

Filter choice: the installed SDK (openai-agents 0.22) provides
``agents.extensions.handoff_filters.remove_all_tools``, so ``build_escalation_handoff`` passes
that directly as the handoff ``input_filter``. ``filter_history``/``describe_history`` remain
the spec-allowed local equivalent for the demo check and the fallback used only when the SDK
helper is unavailable.
"""

from __future__ import annotations

from typing import Any, Literal

from agents import Agent, Handoff, RunContextWrapper, handoff
from agents.extensions.handoff_filters import HandoffInputData
from agents.items import (
    HandoffCallItem,
    HandoffOutputItem,
    MCPApprovalRequestItem,
    MCPApprovalResponseItem,
    MCPListToolsItem,
    ReasoningItem,
    ToolApprovalItem,
    ToolCallItem,
    ToolCallOutputItem,
    ToolSearchCallItem,
    ToolSearchOutputItem,
)
from pydantic import BaseModel, Field

from shopdesk.context import ShopContext
from shopdesk.orders import LineItem

try:
    from agents.extensions.handoff_filters import remove_all_tools as _sdk_remove_all_tools
except ImportError:
    _sdk_remove_all_tools = None

EscalationReason = Literal[
    "not_in_catalogue",
    "out_of_stock",
    "turn_ceiling",
    "customer_requested_human",
    "customer_unhappy",
]

ESCALATION_REASONS: tuple[EscalationReason, ...] = (
    "not_in_catalogue",
    "out_of_stock",
    "turn_ceiling",
    "customer_requested_human",
    "customer_unhappy",
)

TOOL_ITEM_TYPES: tuple[type, ...] = (
    ToolCallItem,
    ToolCallOutputItem,
    HandoffCallItem,
    HandoffOutputItem,
    ToolSearchCallItem,
    ToolSearchOutputItem,
    ReasoningItem,
    MCPListToolsItem,
    MCPApprovalRequestItem,
    MCPApprovalResponseItem,
    ToolApprovalItem,
)

_TOOL_TYPE_STRINGS: frozenset[str] = frozenset(
    {
        "function_call",
        "function_call_output",
        "computer_call",
        "computer_call_output",
        "file_search_call",
        "tool_search_call",
        "tool_search_output",
        "web_search_call",
        "mcp_call",
        "mcp_list_tools",
        "mcp_approval_request",
        "mcp_approval_response",
        "reasoning",
        "code_interpreter_call",
        "image_generation_call",
        "local_shell_call",
        "local_shell_call_output",
        "shell_call",
        "shell_call_output",
        "apply_patch_call",
        "apply_patch_call_output",
        "custom_tool_call",
        "custom_tool_call_output",
        "hosted_tool_call",
        "program",
        "program_output",
    }
)


class EscalationRequest(BaseModel):
    """Typed handoff input: a closed reason, a short summary and the basket (FR-10)."""

    reason: EscalationReason
    summary: str = Field(max_length=200)
    basket_snapshot: list[LineItem] = []

    @classmethod
    def from_context(
        cls, reason: EscalationReason, summary: str, context: ShopContext
    ) -> EscalationRequest:
        """Build a request from the live shop context, snapshotting the basket (FR-10)."""
        return cls(
            reason=reason,
            summary=summary,
            basket_snapshot=[line.model_copy() for line in context.basket],
        )


def _is_tool_activity(item: Any) -> bool:
    """True for items that carry tool activity and must not cross the handoff (FR-10)."""
    if isinstance(item, TOOL_ITEM_TYPES):
        return True
    if isinstance(item, dict):
        return item.get("type") in _TOOL_TYPE_STRINGS
    return "ToolCall" in type(item).__name__


def filter_history(items: list[Any]) -> list[Any]:
    """Return the history with tool activity removed, keeping user/assistant messages (FR-10).

    Unknown item types that are not obviously tool activity are kept, so a new SDK item kind
    is preserved by default rather than silently dropped.
    """
    return [item for item in items if not _is_tool_activity(item)]


def describe_history(items: list[Any]) -> dict[str, Any]:
    """Report the before/after of the transfer for the demo check (SC-006)."""
    kept = filter_history(items)
    removed = [str(item) for item in items if _is_tool_activity(item)]
    return {"before": len(items), "after": len(kept), "removed": removed}


def _apply_filter_history(data: HandoffInputData) -> HandoffInputData:
    """Fallback handoff input filter built on ``filter_history`` (FR-10)."""
    history = data.input_history
    filtered_history = (
        tuple(filter_history(list(history))) if isinstance(history, tuple) else history
    )
    input_items = data.input_items
    filtered_input_items = (
        tuple(filter_history(list(input_items))) if input_items is not None else None
    )
    return data.clone(
        input_history=filtered_history,
        pre_handoff_items=tuple(filter_history(list(data.pre_handoff_items))),
        new_items=tuple(filter_history(list(data.new_items))),
        input_items=filtered_input_items,
    )


_INPUT_FILTER = (
    _sdk_remove_all_tools if _sdk_remove_all_tools is not None else _apply_filter_history
)


def _on_escalation(
    context: RunContextWrapper[Any], request: EscalationRequest
) -> None:
    """Mark the session escalated so the handoff cannot loop (FR-10)."""
    shop_context = context.context
    if isinstance(shop_context, ShopContext):
        shop_context.escalated = True


def build_escalation_handoff(escalation_agent: Agent[Any]) -> Handoff[Any, Any]:
    """Build the typed escalation handoff with a tool-stripping filter (FR-10).

    The installed SDK (openai-agents 0.22) requires an ``on_handoff`` whenever ``input_type``
    is set, so the typed payload is also recorded on the session here.
    """
    return handoff(
        agent=escalation_agent,
        input_type=EscalationRequest,
        input_filter=_INPUT_FILTER,
        on_handoff=_on_escalation,
    )
