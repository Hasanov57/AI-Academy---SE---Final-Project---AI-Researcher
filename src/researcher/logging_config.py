"""Centralized standard-library logging setup."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure a concise timestamped format for console and Docker logs."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
