"""FR-10 / SC-006: escalation travels with a typed reason and a tool-free history.

The reason is a value from a closed set (not a sentence), and the transcript handed to the human
is filtered of tool activity — call items, outputs and reasoning — while every user and
assistant message is kept. The item count drops by exactly the number of tool items removed.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from shopdesk.escalation import (
    ESCALATION_REASONS,
    EscalationRequest,
    describe_history,
    filter_history,
)


class ToolCallItem:
    """A minimal stand-in for the SDK's tool-call item (recognised by class name)."""

    def __init__(self, name: str) -> None:
        self.name = name


class ToolCallOutputItem:
    """A minimal stand-in for the SDK's tool-output item (recognised by class name)."""

    def __init__(self, output: str) -> None:
        self.output = output


def _history() -> list[Any]:
    return [
        {"role": "user", "content": "what does the kettle cost?"},
        ToolCallItem("lookup_price"),
        {"type": "function_call_output", "output": "SKU KTL-01 — 4200 PKR"},
        {"role": "assistant", "content": "It costs 4200 PKR."},
        ToolCallOutputItem("Added 3 × Electric kettle 1.7L"),
        {"role": "user", "content": "add three, please"},
        {"role": "assistant", "content": "Added three."},
        {"role": "user", "content": "thanks"},
    ]


def test_every_closed_reason_is_accepted() -> None:
    assert len(ESCALATION_REASONS) == 5
    for reason in ESCALATION_REASONS:
        request = EscalationRequest(reason=reason, summary="context", basket_snapshot=[])
        assert request.reason == reason


def test_reason_outside_the_closed_set_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EscalationRequest(reason="just_because", summary="context", basket_snapshot=[])


def test_filter_history_removes_tool_activity_and_keeps_messages() -> None:
    history = _history()
    filtered = filter_history(history)

    assert len(filtered) == 5
    assert all(not isinstance(item, (ToolCallItem, ToolCallOutputItem)) for item in filtered)
    assert all(item.get("type") != "function_call_output" for item in filtered if isinstance(item, dict))
    kept_content = [item.get("content") for item in filtered if isinstance(item, dict)]
    assert "what does the kettle cost?" in kept_content
    assert "It costs 4200 PKR." in kept_content
    assert "thanks" in kept_content


def test_describe_history_reports_before_after_and_removed() -> None:
    history = _history()
    report = describe_history(history)

    assert report["before"] == 8
    assert report["after"] == 5
    assert report["before"] > report["after"]
    assert len(report["removed"]) == 3
    assert report["before"] - report["after"] == len(report["removed"])


def test_describe_history_removed_entries_name_the_tool_items() -> None:
    report = describe_history(_history())
    joined = " ".join(report["removed"])
    assert "lookup_price" in joined or "ToolCall" in joined
    assert "function_call_output" in joined
