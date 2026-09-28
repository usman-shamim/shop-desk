"""Canonical customer-visible sentences.

These are the only strings used for these situations (see
specs/001-shop-desk/contracts/handoff-and-guardrail.md), so tests and demo checks can assert
against them instead of matching loose prose.
"""

from __future__ import annotations

GUARDRAIL_REFUSAL = (
    "I can't confirm that price from our catalogue, so I won't quote it — "
    "a colleague can check it for you."
)
OUT_OF_STOCK = (
    "That item is out of stock right now, so I can't sell it — "
    "I won't hold it without checking."
)
NOT_IN_CATALOGUE = "That item isn't in our catalogue, so I can't price it."
REMOVED_FROM_CATALOGUE = "That item isn't in our catalogue any more, so I can't price it."
TURN_CEILING = (
    "I'm sorry — I've taken this as far as I can. "
    "I'm passing you to a colleague who can finish it with you."
)
ESCALATION_ACK = "I'm handing you to a colleague now, and they have what they need."
QUANTITY_BEYOND_STOCK = (
    "We only have {stock} of {name} — I can put {stock} in this conversation if that helps."
)
TOOL_FAILURE = (
    "I couldn't look that up just now, so I won't guess — could you tell me the item again?"
)
