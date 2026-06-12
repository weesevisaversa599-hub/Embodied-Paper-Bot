# -*- coding: utf-8 -*-
"""Cross-platform scheduler using APScheduler."""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from .config_loader import load_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _run_script(script_name: str) -> None:
    """Execute a script under the project virtual environment Python."""
    script_path = PROJECT_ROOT / "scripts" / script_name
    python_exec = sys.executable
    logger.info(f"Running {script_name} ...")
    try:
        subprocess.run(
            [python_exec, str(script_path)],
            cwd=PROJECT_ROOT,
            check=True,
        )
        logger.info(f"{script_name} finished successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"{script_name} failed with exit code {e.returncode}.")


def start_scheduler(config: Dict[str, Any] = None) -> None:
    """Start the background scheduler with configured fetch and push times."""
    if config is None:
        config = load_config()

    schedule_cfg = config.get("schedule", {})
    fetch_time = schedule_cfg.get("fetch_time", "10:00")
    push_time = schedule_cfg.get("push_time", "10:30")
    tz = schedule_cfg.get("timezone", "Asia/Shanghai")

    fetch_hour, fetch_minute = map(int, fetch_time.split(":"))
    push_hour, push_minute = map(int, push_time.split(":"))

    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        lambda: _run_script("fetch_and_read.py"),
        CronTrigger(hour=fetch_hour, minute=fetch_minute),
        id="fetch_and_read",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: _run_script("push_daily.py"),
        CronTrigger(hour=push_hour, minute=push_minute),
        id="push_daily",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. Fetch at {fetch_time}, push at {push_time} ({tz})."
    )

    try:
        # Keep the main thread alive
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
