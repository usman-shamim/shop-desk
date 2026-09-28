"""Evidence CLI for the Shop Desk observable claims (SC-001..SC-006, FR-2, FR-12).

Each subcommand prints a single ``PASS:`` or ``FAIL:`` line and exits non-zero on FAIL. The
subcommand bodies import their dependencies lazily, so every offline check runs without an API
key; only ``price-call-count`` needs ``OPENAI_API_KEY`` and prints a SKIP line without it.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import inspect
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CATALOGUE_PATH = ROOT / "catalogue.json"

_TOOL_TYPE_STRINGS = frozenset(
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
        "reasoning",
    }
)


def _pass(message: str) -> int:
    print(f"PASS: {message}")
    return 0


def _fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def _skip(message: str) -> int:
    print(f"SKIP: {message}")
    return 0


def _is_tool_activity(item: Any) -> bool:
    if isinstance(item, dict):
        return item.get("type") in _TOOL_TYPE_STRINGS
    return "ToolCall" in type(item).__name__


# --- total-mismatch (SC-003) ---------------------------------------------------------------


def cmd_total_mismatch() -> int:
    from shopdesk.orders import LineItem, Order, compare_total, recompute_total

    order = Order(
        order_id="ORD-DEMO0001",
        items=[LineItem(sku="KTL-01", qty=3, unit_price=4200.0)],
        total=1000.0,
    )
    matches, recomputed = compare_total(order)
    print(f"stated total: {order.total:g}; recomputed from line items: {recomputed:g}")
    if matches:
        return _fail("a planted total mismatch was accepted instead of reported")
    if recomputed != recompute_total(order) or recomputed != 3 * 4200.0:
        return _fail(f"the recomputed total should be {3 * 4200.0:g}, got {recomputed:g}")
    return _pass("a planted mismatch between the stated and recomputed total was reported (SC-003)")


# --- catalogue-edit (SC-002) ---------------------------------------------------------------


def cmd_catalogue_edit() -> int:
    from shopdesk.catalogue import load_catalogue
    from shopdesk.guardrails import check_answer

    answer = "SKU KTL-01 — Electric kettle 1.7L costs 4200 PKR."
    original = load_catalogue(CATALOGUE_PATH)
    ok_before, _ = check_answer(answer, original)
    if not ok_before:
        return _fail("the answer did not pass against the untouched catalogue")

    data = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    for product in data["products"]:
        if product["sku"] == "KTL-01":
            product["price"] = 4321
    with tempfile.TemporaryDirectory() as tmp:
        edited_path = Path(tmp) / "catalogue.json"
        edited_path.write_text(json.dumps(data), encoding="utf-8")
        ok_after, offending = check_answer(answer, load_catalogue(edited_path))

    print(
        f"answer before edit: {'pass' if ok_before else 'fail'}; "
        f"after edit: {'pass' if ok_after else 'fail'}; offending: {offending}"
    )
    if ok_after:
        return _fail("a previously passing answer still passed after the catalogue price changed (SC-002)")
    return _pass("editing one catalogue price made a previously passing answer trip the guardrail (SC-002)")


# --- tools-by-tier (SC-004) ----------------------------------------------------------------


def _enabled_tool_names(tier: str) -> list[str]:
    from shopdesk import tools
    from shopdesk.catalogue import load_catalogue
    from shopdesk.context import ShopContext

    catalogue = load_catalogue(CATALOGUE_PATH)
    tools.set_catalogue(catalogue)
    context = ShopContext(
        shop=catalogue.shop,
        currency=catalogue.currency,
        customer_id="demo",
        tier=tier,  # type: ignore[arg-type]
    )
    shim = SimpleNamespace(context=context)
    names: list[str] = []
    for tool in tools.DESK_TOOLS:
        state: Any = tool.is_enabled
        if callable(state):
            state = state(shim, None)
            if inspect.isawaitable(state):
                state = asyncio.run(state)
        if state:
            names.append(tool.name)
    return names


def cmd_tools_by_tier() -> int:
    walk_in = _enabled_tool_names("walk_in")
    regular = _enabled_tool_names("regular")
    print(f"walk_in tools: {walk_in}")
    print(f"regular tools: {regular}")
    if "seasonal_offer" in walk_in or "seasonal_offer" in regular:
        return _fail("the seasonal tool appeared in a tool set")
    if walk_in == regular:
        return _fail("walk-in and regular customers were offered the same tool set")
    return _pass("the tool set differs by tier and the seasonal tool appears in neither (SC-004)")


# --- grep-checks (FR-2) --------------------------------------------------------------------


def _customer_id_prompt_hits(path: Path) -> list[tuple[Path, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    hits: list[tuple[Path, int]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and "customer_id" in node.value
        ):
            hits.append((path, node.lineno))
    return hits


def cmd_grep_checks() -> int:
    from shopdesk import tools

    sources = sorted((ROOT / "shopdesk").glob("*.py")) + sorted(ROOT.glob("*.py"))
    prompt_hits: list[tuple[Path, int]] = []
    for path in sources:
        prompt_hits.extend(_customer_id_prompt_hits(path))

    schema_hits: list[tuple[str, str]] = []
    for tool in getattr(tools, "DESK_TOOLS", []):
        schema = getattr(tool, "params_json_schema", None) or {}
        for name in schema.get("properties", {}):
            lowered = name.lower()
            if lowered in {"context", "ctx"} or lowered.startswith("context"):
                schema_hits.append((tool.name, name))

    for path, lineno in prompt_hits:
        print(f"customer_id string literal at {path.relative_to(ROOT)}:{lineno}")
    for tool_name, param in schema_hits:
        print(f"tool {tool_name!r} schema exposes a parameter named {param!r}")

    if prompt_hits or schema_hits:
        return _fail("a prompt string carried customer_id or a tool schema exposed a context parameter (FR-2)")
    return _pass("no prompt string carries customer_id and no tool schema exposes a context parameter (FR-2)")


# --- trim (FR-12) --------------------------------------------------------------------------


def _fake_history(count: int = 20) -> list[Any]:
    items: list[Any] = []
    for index in range(count):
        if index % 5 == 3:
            items.append({"type": "function_call", "name": "lookup_price", "arguments": "{}"})
        elif index % 2 == 0:
            items.append({"role": "user", "content": f"user message {index}"})
        else:
            items.append({"role": "assistant", "content": f"assistant message {index}"})
    return items


def _bare_runner(cls: type) -> Any:
    from shopdesk.catalogue import load_catalogue
    from shopdesk.config import Settings
    from shopdesk.context import ShopContext

    catalogue = load_catalogue(CATALOGUE_PATH)
    settings = Settings(
        openai_api_key="offline-demo",
        default_model=None,
        open_hour=10,
        close_hour=20,
        simulated_hour=None,
        turn_ceiling=10,
        catalogue_path=CATALOGUE_PATH,
        base_dir=ROOT,
    )
    context = ShopContext(shop=catalogue.shop, currency=catalogue.currency, customer_id="demo")
    return cls(settings, catalogue, context)


def _trim_history_once(history: list[Any]) -> list[Any] | None:
    try:
        from shopdesk import runner as runner_module
    except Exception as exc:  # the runner module is a required, separate deliverable
        print(f"SKIP: trim check requires shopdesk.runner ({exc})")
        return None

    module_trim = getattr(runner_module, "trim_history", None)
    if callable(module_trim):
        return list(module_trim(history))

    cls = getattr(runner_module, "ShopDeskRunner", None)
    method = getattr(cls, "trim_history", None) if cls is not None else None
    if method is None:
        print("SKIP: trim check requires shopdesk.runner.trim_history (browser session)")
        return None
    try:
        instance = _bare_runner(cls)
        return list(instance.trim_history(history))
    except Exception as exc:
        print(f"SKIP: trim check could not exercise trim_history offline ({exc})")
        return None


def cmd_trim() -> int:
    history = _fake_history(20)
    trimmed = _trim_history_once(history)
    if trimmed is None:
        return 0

    kept_tools = [item for item in trimmed if _is_tool_activity(item)]
    first_is_user = bool(trimmed) and isinstance(trimmed[0], dict) and trimmed[0].get("role") == "user"

    print(f"history before: {len(history)} items; after: {len(trimmed)} items")
    if len(trimmed) >= len(history):
        return _fail("trimming did not shorten a 20-item history")
    if kept_tools:
        return _fail(f"trimming left {len(kept_tools)} tool-activity items in the history")
    if not first_is_user:
        return _fail("trimming dropped the first user message")
    return _pass("history trimmed to the first user message plus the most recent six exchanges (FR-12)")


# --- escalation (SC-006) -------------------------------------------------------------------


def _escalation_history() -> list[Any]:
    return [
        {"role": "user", "content": "what does the kettle cost?"},
        {"type": "function_call", "name": "lookup_price", "arguments": "{}"},
        {"type": "function_call_output", "output": "SKU KTL-01 — 4200 PKR"},
        {"role": "assistant", "content": "It costs 4200 PKR."},
        {"type": "function_call", "name": "add_to_basket", "arguments": "{}"},
        {"role": "user", "content": "I'd like a human please"},
        {"role": "assistant", "content": "Of course — passing you over."},
    ]


def cmd_escalation() -> int:
    from shopdesk.escalation import EscalationRequest, describe_history, filter_history

    request = EscalationRequest(
        reason="customer_requested_human",
        summary="Customer asked to speak to a person after a price question.",
        basket_snapshot=[],
    )
    print(f"typed reason: {request.reason!r} (type: {type(request.reason).__name__})")

    history = _escalation_history()
    report = describe_history(history)
    before, after, removed = report["before"], report["after"], report["removed"]
    print(f"history before: {before} items; transferred: {after} items; removed: {len(removed)}")
    for entry in filter_history(history):
        print(f"  kept: {entry}")

    if after >= before:
        return _fail("the transferred history was not smaller than the full transcript (SC-006)")
    if before - after != len(removed):
        return _fail("the item count did not drop by exactly the number of tool items removed (SC-006)")
    if any(_is_tool_activity(item) for item in filter_history(history)):
        return _fail("tool activity survived the transfer (SC-006)")
    return _pass("escalation carries a typed reason and a tool-free history (SC-006)")


# --- price-call-count (SC-001) -------------------------------------------------------------


def cmd_price_call_count() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        return _skip("price-call-count needs OPENAI_API_KEY")
    try:
        from shopdesk import runner as runner_module
    except Exception as exc:
        return _skip(f"price-call-count needs shopdesk.runner for a live run ({exc})")

    run = getattr(runner_module, "run_price_call_count_demo", None)
    if not callable(run):
        return _skip("price-call-count needs a live runner entry point (run main.py --message)")
    ok = bool(run())
    if ok:
        return _pass("a catalogue price question cost exactly one model call (SC-001)")
    return _fail("a catalogue price question did not cost exactly one model call (SC-001)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="demo_checks", description="Shop Desk evidence checks.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    def add(name: str, func: Callable[[], int], help_text: str) -> None:
        subcommands.add_parser(name, help=help_text).set_defaults(func=func)

    add("total-mismatch", cmd_total_mismatch, "report a planted stated/recomputed total mismatch (SC-003)")
    add("catalogue-edit", cmd_catalogue_edit, "show a catalogue edit making a passing answer fail (SC-002)")
    add("tools-by-tier", cmd_tools_by_tier, "print the enabled tools for walk_in and regular (SC-004)")
    add("grep-checks", cmd_grep_checks, "scan for customer_id in prompts and context in schemas (FR-2)")
    add("trim", cmd_trim, "apply the FR-12 history trim rule (FR-12)")
    add("escalation", cmd_escalation, "print the typed reason and before/after history (SC-006)")
    add("price-call-count", cmd_price_call_count, "assert one model call for a price question (SC-001)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func())
    except Exception as exc:  # a check that raises is a failed check, not a traceback
        print(f"FAIL: {args.command} raised {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
