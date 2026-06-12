# -*- coding: utf-8 -*-
"""Low-cost pre-filtering and coarse ranking module.

This module reduces the number of expensive LLM calls by filtering out
obviously irrelevant papers and sorting the rest by keyword relevance.
"""

from typing import List, Dict, Any


# Core embodied AI / VLA keywords used for coarse relevance scoring.
CORE_KEYWORDS = [
    "embodied",
    "vision-language-action",
    "vla",
    "robot",
    "robotic",
    "manipulation",
    "navigation",
    "locomotion",
    "humanoid",
    "reinforcement learning",
    "imitation learning",
    "diffusion policy",
    "world model",
    "sim-to-real",
    "reasoning",
    "planning",
    "foundation model",
    "large language model",
    "vision language model",
    "data scaling",
]

# Keywords that usually indicate non-embodied-AI content.
EXCLUDE_KEYWORDS = [
    "medical",
    "surgical",
    "finance",
    "stock",
    "climate",
    "pure math",
    "theorem",
    "chemistry",
    "biology",
    "survey",
]


def is_relevant(paper: Dict[str, Any]) -> bool:
    """Return False if the paper should be excluded based on keyword rules."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return not any(kw in text for kw in EXCLUDE_KEYWORDS)


def relevance_score(paper: Dict[str, Any]) -> int:
    """Compute a coarse relevance score based on keyword matches."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    score = 0
    for kw in CORE_KEYWORDS:
        score += text.count(kw)
    return score


def rank_papers(papers: List[Dict[str, Any]], top_k: int = 15) -> List[Dict[str, Any]]:
    """Filter and rank papers; return the top-k candidates for LLM classification."""
    scored = []
    for p in papers:
        if not is_relevant(p):
            continue
        s = relevance_score(p)
        if s > 0:
            p["coarse_score"] = s
            scored.append(p)

    scored.sort(key=lambda x: x["coarse_score"], reverse=True)
    return scored[:top_k]
