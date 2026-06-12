#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-platform unified entry point. Run this to start the scheduler."""

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from src.scheduler import start_scheduler


def setup_logging(logs_dir: Path = PROJECT_ROOT / "logs") -> None:
    """Configure loguru to write rotating daily logs."""
    logs_dir.mkdir(exist_ok=True)
    logger.add(
        logs_dir / "bot_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
        level="INFO",
    )


if __name__ == "__main__":
    setup_logging()
    start_scheduler()
