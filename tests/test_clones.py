"""FR-9 / NFR-2: the pricing and escalation agents are clones of one base agent.

The clones share `tools`, `handoffs` and `output_type` by object identity, own their own
`instructions` and `model_settings`, and neither restates a model (so both inherit the process
default), while the order agent carries the one deliberate agent-level model override.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("agents")

from shopdesk.agents import (
    base_specialist,
    desk_agent,
    escalation_agent,
    order_agent,
    pricing_agent,
    show_clone_identity,
)


def _flatten_bools(value: Any) -> list[bool]:
    if isinstance(value, dict):
        return [flag for item in value.values() for flag in _flatten_bools(item)]
    if isinstance(value, (list, tuple, set)):
        return [flag for item in value for flag in _flatten_bools(item)]
    if isinstance(value, bool):
        return [value]
    return []


def test_clones_share_tools_handoffs_and_output_type_by_identity() -> None:
    assert pricing_agent.tools is escalation_agent.tools
    assert pricing_agent.tools is base_specialist.tools
    assert pricing_agent.handoffs is escalation_agent.handoffs
    assert pricing_agent.output_type is escalation_agent.output_type


def test_clones_own_their_instructions_and_model_settings() -> None:
    assert pricing_agent.instructions is not escalation_agent.instructions
    assert pricing_agent.model_settings is not escalation_agent.model_settings


def test_show_clone_identity_reports_shared_and_owned() -> None:
    report = show_clone_identity()
    assert isinstance(report, dict)
    assert report
    flags = _flatten_bools(report)
    if flags:
        assert True in flags
        assert False in flags


def test_neither_specialist_clone_declares_a_model() -> None:
    assert pricing_agent.model is None
    assert escalation_agent.model is None
    assert desk_agent.model is None


def test_order_agent_declares_its_own_model() -> None:
    assert isinstance(order_agent.model, str)
    assert order_agent.model.strip()
