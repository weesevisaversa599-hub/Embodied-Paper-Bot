#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily push script: read top papers from DB and send via PushPlus."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from src.config_loader import load_config
from src.database import PaperDatabase
from src.message_builder import build_daily_message, split_message
from src.pusher import build_pusher


def main() -> None:
    config = load_config()
    paths_cfg = config.get("paths", {})
    data_dir = PROJECT_ROOT / paths_cfg.get("data_dir", "data")
    logs_dir = PROJECT_ROOT / paths_cfg.get("logs_dir", "logs")
    logs_dir.mkdir(exist_ok=True)
    logger.add(logs_dir / "push_{time:YYYY-MM-DD}.log", encoding="utf-8")

    db = PaperDatabase(data_dir / "papers.db")

    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Starting daily push for {today}")

    push_cfg = config["push"]
    max_papers = push_cfg.get("max_papers_per_day", 3)

    # Try today first, then fall back to previous days (handles timezone / arXiv publish delays)
    top_papers = []
    for day_offset in range(3):
        date_str = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        top_papers = db.get_top_unpushed_papers(date_str, limit=max_papers)
        if top_papers:
            today = date_str
            break

    logger.info(f"Found {len(top_papers)} papers to push for {today}")

    if not top_papers:
        logger.info("No papers to push today.")
        return

    message = build_daily_message(top_papers)
    chunks = split_message(message, max_length=1800)

    try:
        pusher = build_pusher(push_cfg)
    except Exception as e:
        logger.error(f"Failed to create pusher: {e}")
        return

    title = f"具身智能每日精选（{today}）"

    for idx, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            chunk_title = f"{title} [{idx}/{len(chunks)}]"
        else:
            chunk_title = title

        result = pusher.send(title=chunk_title, content=chunk)
        status = "success" if result["success"] else "failed"

        for paper in top_papers:
            db.save_push_record(
                arxiv_id=paper["arxiv_id"],
                push_date=today,
                channel="pushplus",
                status=status,
                response=result["response"],
            )

        if not result["success"]:
            logger.error(f"Push chunk {idx} failed: {result['response']}")
        else:
            logger.info(f"Push chunk {idx} succeeded.")


if __name__ == "__main__":
    main()
