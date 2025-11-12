from __future__ import annotations
import os, yaml
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {}

def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg
