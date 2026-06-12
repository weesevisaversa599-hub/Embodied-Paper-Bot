# -*- coding: utf-8 -*-
"""WeChat message formatting module."""

from datetime import datetime
from typing import List, Dict, Any


def _join_tags(tags: List[str]) -> str:
    return " · ".join(str(t) for t in tags) if tags else "N/A"


def build_daily_message(papers: List[Dict[str, Any]]) -> str:
    """Build a Markdown-formatted daily digest for up to 3 papers."""
    today = datetime.now().strftime("%Y-%m-%d")
    if not papers:
        return f"📚 具身智能每日精选（{today}）\n\n今天没有新论文。"

    lines = [f"📚 具身智能每日精选（{today}）", ""]

    for idx, p in enumerate(papers, 1):
        tags = []
        tags.extend(p.get("method_tags", []))
        tags.extend(p.get("task_tags", []))
        tags.extend(p.get("hot_directions", []))
        tags = list(dict.fromkeys(tags))  # deduplicate while preserving order

        lines.append(f"【{idx}】{p.get('title', 'Untitled')}")
        lines.append(f"🏷️ 标签：{_join_tags(tags)}")
        lines.append(f"💡 核心思想：{p.get('core_idea', '')}")
        lines.append(f"📝 方法概括：{p.get('summary', '')}")
        lines.append(f"🎯 推荐理由：{p.get('recommend_reason', '')}")
        lines.append(f"🔥 顶会借鉴点：{p.get('innovation_for_top_conferences', '')}")
        lines.append(f"📖 能学到什么：{p.get('what_to_learn', '')}")
        lines.append(f"⭐ 推荐分数：{p.get('score', 0.0):.1f}/10")
        lines.append(f"🔗 {p.get('abs_url', '')}")

        if idx < len(papers):
            lines.append("\n---\n")

    return "\n".join(lines)


def split_message(text: str, max_length: int = 1800) -> List[str]:
    """Split a long message into multiple chunks to avoid WeChat truncation."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Try to split at a natural boundary
        split_pos = text.rfind("\n---\n", 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind("\n", 0, max_length)
        if split_pos == -1:
            split_pos = max_length
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    return chunks
