from __future__ import annotations
import os
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {}

def load_config(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - triggered only in dep-lite environments
        raise RuntimeError("PyYAML is required to load configuration files; install via requirements.txt") from exc
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg
