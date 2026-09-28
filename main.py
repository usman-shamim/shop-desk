"""CLI entry point for Shop Desk.

Serves FR-4 (a simulated clock via ``--hour`` and printing the resolved instructions before
any model call), FR-12 (a conversation the demo scripts can drive one turn at a time) and
NFR-1 (configuration failures exit with one readable sentence on stderr, never a traceback).
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import sys
import uuid
from typing import Sequence, cast

from shopdesk.catalogue import Catalogue, CatalogueError, load_catalogue
from shopdesk.config import ConfigError, Settings, load_settings
from shopdesk.context import TIERS, ShopContext, Tier
from shopdesk.runner import ShopDeskRunner

EXIT_COMMANDS = {"exit", "quit"}


def build_parser() -> argparse.ArgumentParser:
    """The CLI surface: tier, simulated hour, prompt preview and a one-shot turn."""
    parser = argparse.ArgumentParser(prog="shop-desk", description="Talk to the Shop Desk.")
    parser.add_argument(
        "--tier", choices=TIERS, default="walk_in", help="customer tier (default: walk_in)"
    )
    parser.add_argument(
        "--hour", type=int, default=None, help="simulated clock hour (FR-4); overrides SHOP_SIMULATED_HOUR"
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        dest="print_prompt",
        help="print the resolved instructions and exit before any model call (FR-4)",
    )
    parser.add_argument(
        "--message", default=None, help="run one turn, print the reply and the cost line, then exit"
    )
    parser.add_argument(
        "--session", default=None, help="session/customer identifier (default: a short random id)"
    )
    return parser


def load_runtime() -> tuple[Settings, Catalogue]:
    """Load configuration and catalogue, or exit with the single sentence the error carries (NFR-1)."""
    try:
        settings = load_settings()
        catalogue = load_catalogue(settings.catalogue_path)
    except (ConfigError, CatalogueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    return settings, catalogue


def build_runner(
    args: argparse.Namespace, settings: Settings, catalogue: Catalogue
) -> ShopDeskRunner:
    """One context per session; the customer id is the session id so baskets never merge."""
    session = args.session or uuid.uuid4().hex[:8]
    if args.hour is not None:
        settings = dataclasses.replace(settings, simulated_hour=args.hour)
    context = ShopContext(
        shop=catalogue.shop,
        currency=catalogue.currency,
        customer_id=session,
        tier=cast(Tier, args.tier),
        session_id=session,
    )
    return ShopDeskRunner(settings, catalogue, context)


def converse(runner: ShopDeskRunner) -> None:
    """Interactive REPL; the cost line is printed once the conversation ends (FR-11)."""
    try:
        while True:
            try:
                line = input("you> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            text = line.strip()
            if text.lower() in EXIT_COMMANDS:
                break
            if not text:
                continue
            reply = asyncio.run(runner.run_turn(text))
            print(f"desk> {reply}")
    finally:
        print(runner.cost_line())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings, catalogue = load_runtime()
    runner = build_runner(args, settings, catalogue)

    if args.print_prompt:
        print(runner.resolve_prompt())
        return 0

    if args.message is not None:
        print(asyncio.run(runner.run_turn(args.message)))
        print(runner.cost_line())
        return 0

    converse(runner)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
