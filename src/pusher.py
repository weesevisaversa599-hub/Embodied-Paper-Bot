# -*- coding: utf-8 -*-
"""Push adapters for multiple channels."""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any

import requests


class BasePusher(ABC):
    """Abstract base class for push channels."""

    @abstractmethod
    def send(self, title: str, content: str) -> Dict[str, Any]:
        """Send a message and return status info."""
        pass


class PushPlusPusher(BasePusher):
    """Push message to personal WeChat through PushPlus service."""

    API_URL = "http://www.pushplus.plus/send"

    def __init__(self, token: str):
        self.token = token

    def send(self, title: str, content: str) -> Dict[str, Any]:
        payload = {
            "token": self.token,
            "title": title,
            "content": content,
            "template": "markdown",
        }
        try:
            resp = requests.post(self.API_URL, json=payload, timeout=30)
            resp.raise_for_status()
            return {
                "success": resp.json().get("code") == 200,
                "response": resp.text,
            }
        except Exception as e:
            return {
                "success": False,
                "response": str(e),
            }


class FeishuPusher(BasePusher):
    """Push message to Feishu (Lark) group via webhook bot."""

    def __init__(self, webhook_url: str, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret

    def send(self, title: str, content: str) -> Dict[str, Any]:
        """Send a text/markdown message to Feishu bot."""
        payload = {
            "msg_type": "text",
            "content": {
                "text": f"{title}\n\n{content}",
            },
        }
        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.post(
                self.webhook_url,
                headers=headers,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": data.get("code") == 0,
                "response": resp.text,
            }
        except Exception as e:
            return {
                "success": False,
                "response": str(e),
            }


class ClawPusher(BasePusher):
    """Push message to a local Kimi Claw session via its messages API.

    Default endpoint: POST http://localhost:18789/api/sessions/main/messages
    Default payload:  {"role": "user", "content": "<title>\n\n<content>"}

    If the endpoint expects a different schema, set `claw_payload_template`
    in config. Use `{title}` and `{content}` as placeholders.
    """

    def __init__(
        self,
        webhook_url: str,
        headers: Dict[str, str] = None,
        payload_template: str = None,
    ):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.payload_template = payload_template

    def send(self, title: str, content: str) -> Dict[str, Any]:
        text = f"{title}\n\n{content}"
        if self.payload_template:
            raw_payload = self.payload_template.format(title=title, content=content)
            payload = json.loads(raw_payload)
        else:
            payload = {"role": "user", "content": text}

        try:
            resp = requests.post(
                self.webhook_url,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return {
                "success": 200 <= resp.status_code < 300,
                "response": resp.text,
            }
        except Exception as e:
            return {
                "success": False,
                "response": str(e),
            }


def build_pusher(push_cfg: Dict[str, Any]) -> BasePusher:
    """Factory function that creates a pusher based on config."""
    channel = push_cfg.get("channel", "pushplus")

    if channel == "pushplus":
        return PushPlusPusher(token=push_cfg["pushplus_token"])

    if channel == "feishu":
        return FeishuPusher(
            webhook_url=push_cfg["feishu_webhook_url"],
            secret=push_cfg.get("feishu_secret"),
        )

    if channel == "claw":
        return ClawPusher(
            webhook_url=push_cfg["claw_webhook_url"],
            headers=push_cfg.get("claw_headers"),
            payload_template=push_cfg.get("claw_payload_template"),
        )

    raise ValueError(f"Unsupported push channel: {channel}")
