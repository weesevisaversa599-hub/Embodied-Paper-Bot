#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily fetch + classify + deep-read script."""

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

from src.config_loader import load_config
from src.database import PaperDatabase
from src.fetcher import ArxivFetcher
from src.filter_rank import rank_papers
from src.classifier import PaperClassifier
from src.deep_reader import DeepReader


def main() -> None:
    config = load_config()
    paths_cfg = config.get("paths", {})
    data_dir = PROJECT_ROOT / paths_cfg.get("data_dir", "data")
    logs_dir = PROJECT_ROOT / paths_cfg.get("logs_dir", "logs")
    logs_dir.mkdir(exist_ok=True)
    logger.add(logs_dir / "fetch_{time:YYYY-MM-DD}.log", encoding="utf-8")

    db = PaperDatabase(data_dir / "papers.db")

    today = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Starting fetch_and_read for {today}")

    # 1. Fetch recent papers
    arxiv_cfg = config["arxiv"]
    fetcher = ArxivFetcher(
        queries=arxiv_cfg["queries"],
        max_results_per_query=arxiv_cfg.get("max_results_per_query", 30),
    )
    papers = fetcher.fetch_recent(lookback_days=arxiv_cfg.get("lookback_days", 1))
    logger.info(f"Fetched {len(papers)} papers from arXiv")

    if not papers:
        logger.info("No new papers today.")
        return

    # 2. Save to DB for deduplication, track newly inserted papers
    new_ids = db.save_papers(papers)
    new_papers = [p for p in papers if p["arxiv_id"] in new_ids]
    logger.info(f"{len(new_papers)} papers are new")

    if not new_papers:
        logger.info("No new papers to process.")
        return

    # 3. Coarse filter and rank only the new papers
    candidates = rank_papers(new_papers, top_k=arxiv_cfg.get("candidate_pool_size", 12))
    logger.info(f"Selected {len(candidates)} candidates for classification")

    if not candidates:
        logger.info("No relevant candidates after filtering.")
        return

    # 4. Classify candidates with LLM
    llm_cfg = config["llm"]
    classifier = PaperClassifier(
        api_key=llm_cfg["api_key"],
        model=llm_cfg.get("model", "moonshot-v1-32k"),
        base_url=llm_cfg.get("base_url", "https://api.moonshot.cn/v1"),
        temperature=llm_cfg.get("temperature", 0.3),
        max_retries=llm_cfg.get("max_retries", 3),
        method_tags=config["classification"].get("method_tags", []),
        task_tags=config["classification"].get("task_tags", []),
        hot_directions=config["classification"].get("hot_directions", []),
    )

    classified_ids = []
    for paper in candidates:
        try:
            result = classifier.classify(paper)
            db.save_classification(paper["arxiv_id"], result)
            classified_ids.append(paper["arxiv_id"])
        except Exception as e:
            logger.error(f"Failed to classify {paper['arxiv_id']}: {e}")

    logger.info(f"Classified {len(classified_ids)} papers")

    if not classified_ids:
        logger.info("No papers classified, skipping deep read.")
        return

    # 5. Deep-read the newly classified candidates
    deep_reader = DeepReader(
        api_key=llm_cfg["api_key"],
        model=llm_cfg.get("model", "moonshot-v1-32k"),
        base_url=llm_cfg.get("base_url", "https://api.moonshot.cn/v1"),
        temperature=llm_cfg.get("temperature", 0.3),
        max_retries=llm_cfg.get("max_retries", 3),
        read_pdf=True,
    )

    # Build candidate list from classified IDs, limited by pool size
    max_read = arxiv_cfg.get("candidate_pool_size", 12)
    classified_papers = [p for p in candidates if p["arxiv_id"] in classified_ids][:max_read]
    logger.info(f"Deep-reading {len(classified_papers)} papers")

    read_count = 0
    for paper in classified_papers:
        try:
            result = deep_reader.read(paper)
            db.save_deep_read(paper["arxiv_id"], result)
            read_count += 1
        except Exception as e:
            logger.error(f"Failed to deep-read {paper['arxiv_id']}: {e}")

    logger.info(f"Deep-read {read_count} papers. Ready for push.")


if __name__ == "__main__":
    main()
