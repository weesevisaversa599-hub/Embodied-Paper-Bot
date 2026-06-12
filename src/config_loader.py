# -*- coding: utf-8 -*-
"""Configuration loader with environment-variable expansion."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load config.yaml and expand ${VAR} placeholders from environment."""
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "config.yaml"

    # Load .env file if python-dotenv is installed
    try:
        from dotenv import load_dotenv
        project_root = config_path.parent.parent
        load_dotenv(project_root / ".env")
    except ImportError:
        pass

    with open(config_path, "r", encoding="utf-8") as f:
        raw = f.read()

    expanded = os.path.expandvars(raw)
    return yaml.safe_load(expanded)
