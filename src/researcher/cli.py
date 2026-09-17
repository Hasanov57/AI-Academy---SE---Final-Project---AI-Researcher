"""Command-line entry point required by the Topic 4 specification."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from ai.providers.base import ProviderError
from pydantic import ValidationError

from researcher.bootstrap import build_runtime
from researcher.config import Settings
from researcher.errors import ResearcherError
from researcher.logging_config import configure_logging
from researcher.models import DEFAULT_SOURCES, ResearchRequest, SourceName
from researcher.rendering import render_text
from researcher.storage.postgres import PostgresRepository


def parse_sources(value: str) -> tuple[SourceName, ...]:
    """Parse the comma-separated ``--sources`` option."""
    aliases = {"wikipedia": "wiki", "ddg": "web"}
    raw = [
        aliases.get(piece.strip().casefold(), piece.strip().casefold())
        for piece in value.split(",")
    ]
    try:
        parsed = tuple(SourceName(piece) for piece in raw if piece)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("sources must contain only wiki, arxiv, web") from exc
    if not parsed:
        raise argparse.ArgumentTypeError("at least one source must be selected")
    return tuple(dict.fromkeys(parsed))


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser without causing import-time side effects."""
    parser = argparse.ArgumentParser(prog="researcher", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    ask = commands.add_parser("ask", help="Research one question and print cited results")
    ask.add_argument("question", help="Research question (1-1000 characters)")
    ask.add_argument(
        "--sources",
        type=parse_sources,
        default=DEFAULT_SOURCES,
        metavar="wiki,arxiv,web",
        help="Restrict upstream sources",
    )
    ask.add_argument("--no-cache", action="store_true", help="Bypass cache reads and writes")
    ask.add_argument("--json", action="store_true", help="Print structured JSON")
    ask.add_argument("--offline", action="store_true", help="Use deterministic local providers")
    ask.add_argument(
        "--storage",
        choices=("postgres", "memory"),
        help="Override STORAGE_BACKEND for this command",
    )

    init_db = commands.add_parser("init-db", help="Create PostgreSQL tables")
    init_db.add_argument(
        "--storage",
        choices=("postgres", "memory"),
        default="postgres",
        help=argparse.SUPPRESS,
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    settings = Settings()
    if getattr(args, "storage", None):
        settings = settings.model_copy(update={"storage_backend": args.storage})
    configure_logging(settings.log_level)

    if args.command == "init-db":
        repository = PostgresRepository(settings.database_url.get_secret_value())
        await repository.initialize()
        await repository.close()
        print("Storage initialized successfully.")
        return 0

    if len(args.question) > settings.question_max_length:
        raise ValueError(f"Question exceeds QUESTION_MAX_LENGTH={settings.question_max_length}")
    request = ResearchRequest(
        question=args.question,
        sources=args.sources,
        no_cache=args.no_cache,
    )
    runtime = await build_runtime(settings, offline=args.offline)
    try:
        result = await runtime.researcher.ask(request)
    finally:
        await runtime.close()
    print(result.model_dump_json(indent=2) if args.json else render_text(result))
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    """Parse arguments, run the async command and map failures to exit codes."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = asyncio.run(_run(args))
    except (ResearcherError, ProviderError, ValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    raise SystemExit(code)
