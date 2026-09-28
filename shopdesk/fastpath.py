"""The price fast path (FR-3, R5).

When the model calls the price tool, the run must end with that tool's own output as the final
answer: one model call for the turn, and the model never sees the figure it just quoted. The
behaviour is a `ToolsToFinalOutputFunction` — the SDK calls it with the run context and the
completed tool results, and a `ToolsToFinalOutputResult(is_final_output=True, ...)` ends the
loop at that point.
"""

from __future__ import annotations

from typing import Any, Callable

from agents import (
    FunctionToolResult,
    RunContextWrapper,
    StopAtTools,
    ToolsToFinalOutputResult,
)

from shopdesk.context import ShopContext

FAST_PATH_TOOL_NAME = "lookup_price"


def is_fast_path_tool(name: str) -> bool:
    """True when a tool name is the price lookup that ends the run with its own output."""
    return isinstance(name, str) and name.strip() == FAST_PATH_TOOL_NAME


def _tool_name(result: Any) -> str:
    tool = getattr(result, "tool", None)
    name = getattr(tool, "name", None)
    if isinstance(name, str):
        return name
    qualified = getattr(tool, "qualified_name", None)
    if isinstance(qualified, str):
        return qualified
    return ""


def _output_text(output: Any) -> str:
    """Extract the readable text from whatever shape a tool result carries."""
    if output is None:
        return ""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        text = output.get("text")
        return text if isinstance(text, str) else str(output)
    if isinstance(output, (list, tuple)):
        return " ".join(part for part in (_output_text(item) for item in output) if part)
    text = getattr(output, "text", None)
    if isinstance(text, str):
        return text
    return str(output)


def _fast_path_behavior(
    context: RunContextWrapper[ShopContext], tool_results: list[FunctionToolResult]
) -> ToolsToFinalOutputResult:
    for result in tool_results:
        if is_fast_path_tool(_tool_name(result)):
            final_output = _output_text(getattr(result, "output", None))
            return ToolsToFinalOutputResult(is_final_output=True, final_output=final_output)
    return ToolsToFinalOutputResult(is_final_output=False)


def build_fast_path_behavior() -> Callable[
    [RunContextWrapper[ShopContext], list[FunctionToolResult]], ToolsToFinalOutputResult
]:
    """The `tool_use_behavior` value for the Desk: end the run on the price tool's output."""
    return _fast_path_behavior


def build_stop_at_tools_behavior() -> StopAtTools:
    """The declarative fallback for the same behaviour (the SDK's `StopAtTools` form)."""
    return StopAtTools(stop_at_tool_names=[FAST_PATH_TOOL_NAME])
