# -*- coding: utf-8 -*-
"""LLM-based paper classification module using Kimi (Moonshot) API."""

import json
import re
from typing import Dict, Any, List
from openai import OpenAI


class PaperClassifier:
    def __init__(
        self,
        api_key: str,
        model: str = "moonshot-v1-32k",
        base_url: str = "https://api.moonshot.cn/v1",
        temperature: float = 0.3,
        max_retries: int = 3,
        method_tags: List[str] = None,
        task_tags: List[str] = None,
        hot_directions: List[str] = None,
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
        )
        self.model = model
        self.temperature = temperature
        self.method_tags = method_tags or []
        self.task_tags = task_tags or []
        self.hot_directions = hot_directions or []

    def classify(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Classify a single paper and return a structured JSON result."""
        prompt = self._build_prompt(paper)
        last_error = None
        for attempt in range(2):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in embodied AI and VLA research. "
                            "You must return valid JSON only, no extra text."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            try:
                return self._parse_json(raw)
            except Exception as e:
                last_error = e
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Please return ONLY a valid JSON object with this exact schema:\n\n"
                    "{\"is_embodied_ai\": true, \"method_tags\": [...], \"task_tags\": [...], "
                    "\"hot_directions\": [...], \"confidence\": 0.9, \"relevance_score\": 8.0}\n\n"
                    "Use the original paper info I provided earlier."
                )
        raise last_error

    def _build_prompt(self, paper: Dict[str, Any]) -> str:
        return (
            "You are an expert in embodied AI and Vision-Language-Action (VLA).\n"
            "Read the following arXiv paper title and abstract, determine whether it belongs to embodied AI / VLA, "
            "and assign appropriate tags.\n\n"
            f"Title: {paper.get('title', '')}\n"
            f"Abstract: {paper.get('abstract', '')}\n"
            f"Categories: {', '.join(paper.get('categories', []))}\n\n"
            "Method tags (choose 0-3 from the list or add new ones if needed):\n"
            f"{', '.join(self.method_tags)}\n\n"
            "Task tags (choose 0-3 from the list or add new ones if needed):\n"
            f"{', '.join(self.task_tags)}\n\n"
            "Hot direction tags (choose 0-3 from the list or add new ones if needed):\n"
            f"{', '.join(self.hot_directions)}\n\n"
            "Return strictly as JSON with the following schema:\n"
            "{\n"
            '  "is_embodied_ai": true or false,\n'
            '  "method_tags": ["..."],\n'
            '  "task_tags": ["..."],\n'
            '  "hot_directions": ["..."],\n'
            '  "confidence": 0.0 to 1.0,\n'
            '  "relevance_score": 0 to 10\n'
            "}"
        )

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Parse JSON response robustly."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code fences
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                raise ValueError(f"Invalid JSON from classifier: {raw}")

        return {
            "is_embodied_ai": data.get("is_embodied_ai", True),
            "method_tags": data.get("method_tags", []),
            "task_tags": data.get("task_tags", []),
            "hot_directions": data.get("hot_directions", []),
            "confidence": float(data.get("confidence", 0.0)),
            "relevance_score": float(data.get("relevance_score", 0.0)),
        }
