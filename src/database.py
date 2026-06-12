# -*- coding: utf-8 -*-
"""SQLite database module for paper deduplication, classification,
deep-read results, and push history persistence."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any


class PaperDatabase:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    categories TEXT,
                    published_date TEXT,
                    abs_url TEXT,
                    pdf_url TEXT,
                    fetched_at TEXT NOT NULL,
                    is_relevant INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id TEXT NOT NULL,
                    method_tags TEXT,
                    task_tags TEXT,
                    hot_directions TEXT,
                    confidence REAL,
                    relevance_score REAL,
                    classified_at TEXT NOT NULL,
                    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
                );

                CREATE TABLE IF NOT EXISTS deep_reads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id TEXT NOT NULL,
                    core_idea TEXT,
                    summary TEXT,
                    key_contributions TEXT,
                    what_to_learn TEXT,
                    innovation_for_top_conferences TEXT,
                    recommended_conference TEXT,
                    score REAL,
                    recommend_reason TEXT,
                    read_at TEXT NOT NULL,
                    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
                );

                CREATE TABLE IF NOT EXISTS pushes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arxiv_id TEXT NOT NULL,
                    push_date TEXT NOT NULL,
                    channel TEXT,
                    status TEXT,
                    response TEXT,
                    pushed_at TEXT NOT NULL,
                    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
                );

                CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_date);
                CREATE INDEX IF NOT EXISTS idx_pushes_date ON pushes(push_date);
                """
            )
            conn.commit()

    def save_papers(self, papers: List[Dict[str, Any]]) -> List[str]:
        """Batch save paper metadata, ignoring duplicate arxiv_ids.

        Returns the list of arxiv_ids that were actually inserted.
        """
        now = datetime.now().isoformat()
        inserted_ids: List[str] = []
        with self._connect() as conn:
            for p in papers:
                arxiv_id = p["arxiv_id"]
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO papers
                    (arxiv_id, title, authors, abstract, categories, published_date,
                     abs_url, pdf_url, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        arxiv_id,
                        p["title"],
                        json.dumps(p.get("authors", []), ensure_ascii=False),
                        p.get("abstract", ""),
                        json.dumps(p.get("categories", []), ensure_ascii=False),
                        p.get("published_date", ""),
                        p.get("abs_url", ""),
                        p.get("pdf_url", ""),
                        now,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted_ids.append(arxiv_id)
            conn.commit()
        return inserted_ids

    def paper_exists(self, arxiv_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,)
            ).fetchone()
            return row is not None

    def get_papers_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM papers WHERE published_date = ? ORDER BY fetched_at DESC",
                (date_str,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_unclassified_papers(self, date_str: str) -> List[Dict[str, Any]]:
        """Return papers for a given date that have not been classified yet."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.* FROM papers p
                LEFT JOIN classifications c ON p.arxiv_id = c.arxiv_id
                WHERE p.published_date = ? AND c.id IS NULL
                """,
                (date_str,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def save_classification(self, arxiv_id: str, result: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO classifications
                (arxiv_id, method_tags, task_tags, hot_directions, confidence,
                 relevance_score, classified_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    arxiv_id,
                    json.dumps(result.get("method_tags", []), ensure_ascii=False),
                    json.dumps(result.get("task_tags", []), ensure_ascii=False),
                    json.dumps(result.get("hot_directions", []), ensure_ascii=False),
                    result.get("confidence", 0.0),
                    result.get("relevance_score", 0.0),
                    now,
                ),
            )
            conn.commit()

    def get_classified_candidates(self, date_str: str) -> List[Dict[str, Any]]:
        """Return classified but not-yet-deep-read candidates for a date."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*, c.method_tags, c.task_tags, c.hot_directions,
                       c.confidence, c.relevance_score
                FROM papers p
                JOIN classifications c ON p.arxiv_id = c.arxiv_id
                LEFT JOIN deep_reads d ON p.arxiv_id = d.arxiv_id
                WHERE p.published_date = ? AND d.id IS NULL AND c.relevance_score >= 5.0
                ORDER BY c.relevance_score DESC
                """,
                (date_str,),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def save_deep_read(self, arxiv_id: str, result: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO deep_reads
                (arxiv_id, core_idea, summary, key_contributions, what_to_learn,
                 innovation_for_top_conferences, recommended_conference, score,
                 recommend_reason, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    arxiv_id,
                    result.get("core_idea", ""),
                    result.get("summary", ""),
                    json.dumps(result.get("key_contributions", []), ensure_ascii=False),
                    result.get("what_to_learn", ""),
                    result.get("innovation_for_top_conferences", ""),
                    result.get("recommended_conference", ""),
                    result.get("score", 0.0),
                    result.get("recommend_reason", ""),
                    now,
                ),
            )
            conn.commit()

    def get_top_unpushed_papers(
        self, date_str: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Return the top-N scored, not-yet-pushed papers for a date."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*, c.method_tags, c.task_tags, c.hot_directions,
                       d.core_idea, d.summary, d.key_contributions, d.what_to_learn,
                       d.innovation_for_top_conferences, d.recommended_conference,
                       d.score, d.recommend_reason
                FROM papers p
                JOIN classifications c ON p.arxiv_id = c.arxiv_id
                JOIN deep_reads d ON p.arxiv_id = d.arxiv_id
                LEFT JOIN pushes pu ON p.arxiv_id = pu.arxiv_id AND pu.push_date = ?
                WHERE p.published_date = ? AND pu.id IS NULL
                ORDER BY d.score DESC
                LIMIT ?
                """,
                (date_str, date_str, limit),
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def save_push_record(
        self,
        arxiv_id: str,
        push_date: str,
        channel: str,
        status: str,
        response: str,
    ) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pushes (arxiv_id, push_date, channel, status, response, pushed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (arxiv_id, push_date, channel, status, response, now),
            )
            conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        for key in ["authors", "categories", "method_tags", "task_tags", "hot_directions", "key_contributions"]:
            if key in data and isinstance(data[key], str):
                try:
                    data[key] = json.loads(data[key])
                except json.JSONDecodeError:
                    data[key] = []
        return data
