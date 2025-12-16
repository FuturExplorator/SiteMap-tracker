import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_ACTION_WORDS = [
    "enhance",
    "sharpen",
    "upscale",
    "denoise",
    "restore",
    "remove",
    "erase",
    "clean",
    "convert",
    "generate",
    "create",
    "compress",
    "blur",
    "unblur",
    "colorize",
    "fix",
    "repair",
    "replace",
    "fill",
]

DEFAULT_OBJECT_WORDS = [
    "image",
    "photo",
    "picture",
    "avatar",
    "headshot",
    "logo",
    "background",
    "watermark",
    "text",
    "pdf",
    "video",
    "gif",
    "resume",
    "document",
    "face",
    "noise",
    "blur",
    "meme",
    "poster",
    "banner",
]


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Optional[str]) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "max_urls": 500,
        "sample_strategy": "first",  # or "random"
        "http": {
            "user_agent": "SitemapTools/0.1",
            "timeout": 10,
            "delay": 0.0,
        },
        "rules": {
            "actions": DEFAULT_ACTION_WORDS,
            "objects": DEFAULT_OBJECT_WORDS,
        },
        "llm": {
            "enabled": False,
            "model": None,
            "base_url": None,
            "api_key": None,
            "batch_size": 20,
        },
    }

    if not path:
        return base

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    data: Dict[str, Any]
    if config_path.suffix.lower() in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError("pyyaml is required for YAML config files") from exc
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    else:
        with config_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("Config root must be a JSON/YAML object")

    return _deep_merge(base, data)
