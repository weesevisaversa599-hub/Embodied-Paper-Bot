# -*- coding: utf-8 -*-
"""arXiv paper fetching module."""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import arxiv


class ArxivFetcher:
    def __init__(self, queries: List[str], max_results_per_query: int = 30):
        self.queries = queries
        self.max_results_per_query = max_results_per_query
        self.client = arxiv.Client(
            page_size=100,
            delay_seconds=3,
            num_retries=3,
        )

    def fetch_recent(
        self, lookback_days: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetch papers submitted in the last lookback_days, deduplicated by arxiv_id."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        seen_ids = set()
        all_papers: List[Dict[str, Any]] = []

        for query in self.queries:
            search = arxiv.Search(
                query=query,
                max_results=self.max_results_per_query,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            try:
                for result in self.client.results(search):
                    if result.published.replace(tzinfo=timezone.utc) < cutoff:
                        break
                    if result.entry_id in seen_ids:
                        continue
                    seen_ids.add(result.entry_id)
                    all_papers.append(self._parse_result(result))
            except Exception as e:
                print(f"[Fetcher] Query '{query}' failed: {e}")
                continue

        # Sort by published date descending
        all_papers.sort(key=lambda x: x["published_date"], reverse=True)
        return all_papers

    def _parse_result(self, result: arxiv.Result) -> Dict[str, Any]:
        return {
            "arxiv_id": result.entry_id.split("/")[-1],
            "title": result.title.strip().replace("\n", " "),
            "authors": [str(a) for a in result.authors],
            "abstract": result.summary.strip().replace("\n", " "),
            "categories": result.categories,
            "published_date": result.published.strftime("%Y-%m-%d"),
            "abs_url": result.entry_id,
            "pdf_url": result.pdf_url,
        }
