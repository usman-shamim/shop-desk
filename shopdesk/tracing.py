"""One trace per conversation and tracing configuration (FR-13).

``conversation_trace`` wraps every turn of a session in a single
``trace(workflow_name="shop-desk", group_id=<session_id>)`` so the Desk's turns, the fast-path
turns and the nested specialist runs appear together in one openable trace. ``conversation_span``
opens a nested span for a single turn inside that trace. ``configure_tracing`` keeps tracing
enabled under the shop's own credentials without ever printing the key (FR-13, NFR-1).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any

from agents.tracing import custom_span, set_tracing_disabled, set_tracing_export_api_key, trace

WORKFLOW_NAME = "shop-desk"


@contextmanager
def conversation_trace(session_id: str) -> Iterator[None]:
    """Group a whole conversation — every turn — into one trace keyed by ``session_id`` (FR-13)."""
    with trace(workflow_name=WORKFLOW_NAME, group_id=session_id):
        yield


def conversation_span(session_id: str, turn_index: int) -> AbstractContextManager[Any]:
    """A nested span marking a single turn inside the conversation trace (FR-13)."""
    return custom_span(
        name=f"{WORKFLOW_NAME} turn {turn_index}",
        data={"session_id": session_id, "turn": turn_index},
    )


def configure_tracing(settings: Any) -> None:
    """Keep tracing enabled and export under the shop's own key, read from settings (FR-13)."""
    set_tracing_disabled(False)
    api_key = getattr(settings, "openai_api_key", None)
    if isinstance(api_key, str) and api_key:
        set_tracing_export_api_key(api_key)
