"""Cache helpers for prompt results and persistent LLM output."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data")
CACHE_FILE = CACHE_DIR / "cache_llm.json"


def get_cache_path(path: Path | str | None = None) -> Path:
    """Return the cache file path, optionally overriding the default."""
    if path is None:
        return CACHE_FILE
    return Path(path)


def hash_prompt(text: str) -> str:
    """Generate a stable SHA-256 hash for a prompt string."""
    if not isinstance(text, str):
        raise TypeError("Prompt text must be a string")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_cache(path: Path | str | None = None) -> Dict[str, str]:
    """Load the JSON cache from disk, returning an empty dict when absent or invalid."""
    cache_path = get_cache_path(path)

    if not cache_path.exists():
        return {}

    try:
        with cache_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            logger.warning("Cache file %s contains non-dict JSON; resetting cache.", cache_path)
            return {}
    except json.JSONDecodeError as exc:
        logger.warning("Cache file %s is invalid JSON: %s", cache_path, exc)
        return {}
    except Exception as exc:
        logger.error("Failed to load cache from %s: %s", cache_path, exc)
        return {}


def save_cache(cache: Dict[str, str], path: Path | str | None = None) -> None:
    """Persist the cache dict to disk safely."""
    if not isinstance(cache, dict):
        raise TypeError("Cache must be a dict[str, str]")

    cache_path = get_cache_path(path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with cache_path.open("w", encoding="utf-8") as fp:
            json.dump(cache, fp, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error("Failed to save cache to %s: %s", cache_path, exc)


def clear_cache(path: Path | str | None = None) -> None:
    """Delete the cache file if it exists."""
    cache_path = get_cache_path(path)
    try:
        if cache_path.exists():
            cache_path.unlink()
    except Exception as exc:
        logger.error("Failed to remove cache file %s: %s", cache_path, exc)
