# -*- coding: utf-8 -*-
"""Deep reading and recommendation module using Kimi (Moonshot) API."""

import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.request import urlopen
from openai import OpenAI


try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class DeepReader:
    def __init__(
        self,
        api_key: str,
        model: str = "moonshot-v1-32k",
        base_url: str = "https://api.moonshot.cn/v1",
        temperature: float = 0.3,
        max_retries: int = 3,
        read_pdf: bool = True,
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
        )
        self.model = model
        self.temperature = temperature
        self.read_pdf = read_pdf and fitz is not None

    def read(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-read a paper and return recommendation analysis."""
        pdf_text = ""
        if self.read_pdf and paper.get("pdf_url"):
            try:
                pdf_text = self._download_and_extract(paper["pdf_url"])
            except Exception as e:
                pdf_text = f"[PDF extraction failed: {e}]"

        prompt = self._build_prompt(paper, pdf_text)
        last_error = None
        for attempt in range(2):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert reviewer and mentor in embodied AI. "
                            "Read the paper carefully and give a recommendation analysis from the perspective of "
                            "'what can I learn' and 'what can I borrow for a top-tier conference paper'. "
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
                # Second attempt: add explicit reminder
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Please return ONLY a valid JSON object matching this exact schema:\n\n"
                    "{\"core_idea\": \"...\", \"summary\": \"...\", \"key_contributions\": [...], "
                    "\"what_to_learn\": \"...\", \"innovation_for_top_conferences\": \"...\", "
                    "\"recommended_conference\": \"...\", \"score\": 8.5, \"recommend_reason\": \"...\"}\n\n"
                    "All text values should be in Chinese except recommended_conference."
                )
        raise last_error

    def _download_and_extract(self, pdf_url: str, max_chars: int = 12000) -> str:
        """Download a PDF and extract text with PyMuPDF."""
        if fitz is None:
            return "[PyMuPDF not installed]"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            with urlopen(pdf_url, timeout=60) as resp:
                tmp.write(resp.read())

        text = ""
        try:
            doc = fitz.open(tmp_path)
            for page in doc:
                text += page.get_text()
                if len(text) >= max_chars:
                    break
            doc.close()
        finally:
            tmp_path.unlink(missing_ok=True)

        return text[:max_chars]

    def _build_prompt(self, paper: Dict[str, Any], pdf_text: str) -> str:
        authors = ", ".join(paper.get("authors", [])[:5])
        if len(paper.get("authors", [])) > 5:
            authors += ", et al."

        return (
            "You are an expert reviewer and mentor in embodied AI / VLA.\n"
            "Read the following paper and provide a recommendation analysis in Chinese (except the conference abbreviations).\n"
            "Analyze from two angles:\n"
            "1. What can the reader learn from this paper?\n"
            "2. What innovative points are worth borrowing for top-tier conferences (CVPR, ICRA, ICLR, CoRL, RSS, etc.)?\n\n"
            f"Title: {paper.get('title', '')}\n"
            f"Authors: {authors}\n"
            f"Abstract: {paper.get('abstract', '')}\n"
            f"PDF content (first part): {pdf_text}\n\n"
            "Return strictly as JSON with the following schema. All text values except recommended_conference should be in Chinese:\n"
            "{\n"
            '  "core_idea": "一句话概括核心思想（中文）",\n'
            '  "summary": "3-5句话总结方法/实验/结论（中文）",\n'
            '  "key_contributions": ["贡献点1（中文）", "贡献点2（中文）", "贡献点3（中文）"],\n'
            '  "what_to_learn": "读者能学到的新知识和新思路（中文）",\n'
            '  "innovation_for_top_conferences": "哪些创新点可以借鉴用于顶会（中文）",\n'
            '  "recommended_conference": "最推荐的投稿顶会，如 CVPR / ICRA / ICLR / CoRL / RSS",\n'
            '  "score": 0 to 10,\n'
            '  "recommend_reason": "为什么今天值得读这篇（中文）"\n'
            "}"
        )

    def _parse_json(self, raw: str) -> Dict[str, Any]:
        """Parse JSON response robustly."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                raise ValueError(f"Invalid JSON from deep reader: {raw}")

        return {
            "core_idea": data.get("core_idea", ""),
            "summary": data.get("summary", ""),
            "key_contributions": data.get("key_contributions", []),
            "what_to_learn": data.get("what_to_learn", ""),
            "innovation_for_top_conferences": data.get("innovation_for_top_conferences", ""),
            "recommended_conference": data.get("recommended_conference", ""),
            "score": float(data.get("score", 0.0)),
            "recommend_reason": data.get("recommend_reason", ""),
        }
