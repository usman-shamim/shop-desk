"""The agents: one Desk, one order assembler, and two clones of one base specialist.

FR-1: only the order assembler declares a model (the agent-level override); the Desk and both
specialists declare none and inherit the process default.
FR-9: the pricing and escalation agents are clones of a single base agent, differing only in
instructions and model settings — neither restates the model it inherits.
FR-8: the pricing specialist is exposed to the Desk as a tool that answers with a figure.
"""

from __future__ import annotations

from typing import Any

from agents import Agent, ModelSettings, handoff

from shopdesk import escalation, fastpath, guardrails, hooks, instructions, pricing, tools
from shopdesk.orders import Order

BASE_INSTRUCTIONS = (
    "You are a specialist supporting the Shop Desk. Answer with the facts you are given and "
    "never invent a price, a stock figure or an item identifier."
)

PRICING_SETTINGS = ModelSettings(reasoning={"effort": "low"}, verbosity="low")
ESCALATION_SETTINGS = ModelSettings(reasoning={"effort": "medium"}, verbosity="medium")

ORDER_INSTRUCTIONS = (
    "You assemble orders for the Shop Desk. Read the conversation, put every agreed item into "
    "the order with its catalogue unit price, and return the order as structured data. "
    "Never invent a price: use the unit price the catalogue tools gave you."
)

ESCALATION_INSTRUCTIONS = (
    "You are a senior colleague taking over a conversation the Shop Desk could not finish. "
    "You have the typed reason and the customer's messages. Acknowledge the handover in one "
    "short sentence, then continue helping."
)

base_specialist: Agent[Any] = Agent(
    name="specialist",
    instructions=BASE_INSTRUCTIONS,
    tools=[],
)

pricing_agent: Agent[Any] = base_specialist.clone(
    instructions=pricing.PRICING_INSTRUCTIONS,
    model_settings=PRICING_SETTINGS,
    hooks=hooks.PRICING_HOOKS,
)

escalation_agent: Agent[Any] = base_specialist.clone(
    instructions=ESCALATION_INSTRUCTIONS,
    model_settings=ESCALATION_SETTINGS,
)

order_agent: Agent[Any] = Agent(
    name="order_assembler",
    instructions=ORDER_INSTRUCTIONS,
    model="gpt-5-mini",
    output_type=Order,
    tools=[tools.add_to_basket, tools.confirm_order],
)

desk_agent: Agent[Any] = Agent(
    name="shop_desk",
    instructions=instructions.build_instructions,
    tools=[
        *tools.DESK_TOOLS,
        pricing.build_pricing_tool(pricing_agent),
        pricing.re_quote,
    ],
    tool_use_behavior=fastpath.build_fast_path_behavior(),
    handoffs=[
        handoff(order_agent),
        escalation.build_escalation_handoff(escalation_agent),
    ],
    output_guardrails=guardrails.OUTPUT_GUARDRAILS,
)

DESK_TOOL_NAMES: list[str] = [
    str(getattr(tool, "name", "unnamed")) for tool in desk_agent.tools
]

SPECIALISTS: tuple[Agent[Any], ...] = (pricing_agent, escalation_agent)


def show_clone_identity() -> dict[str, Any]:
    """What the clones share with the base and what they own, by identity (FR-9).

    ``True`` under ``shared`` means the clones and the base hold the same object. ``True`` under
    ``owned`` means they hold the same object for a field they were supposed to override — which
    would be a defect, so the demo asserts those are ``False``.
    """
    return {
        "shared": {
            "tools": pricing_agent.tools is base_specialist.tools
            and escalation_agent.tools is base_specialist.tools,
            "handoffs": pricing_agent.handoffs is base_specialist.handoffs
            and escalation_agent.handoffs is base_specialist.handoffs,
            "output_type": pricing_agent.output_type is base_specialist.output_type
            and escalation_agent.output_type is base_specialist.output_type,
            "name": pricing_agent.name == escalation_agent.name == base_specialist.name,
        },
        "owned": {
            "instructions": pricing_agent.instructions is escalation_agent.instructions,
            "model_settings": pricing_agent.model_settings is escalation_agent.model_settings,
            "hooks": pricing_agent.hooks is escalation_agent.hooks,
        },
        "models": {
            "desk": desk_agent.model,
            "pricing": pricing_agent.model,
            "escalation": escalation_agent.model,
            "order": order_agent.model,
        },
    }
