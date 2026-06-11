# =========================================================
# core/llm.py - Clean, complete, and robust LLM helpers
# =========================================================

import logging
import re
from typing import Any, Dict, Optional

from core.config import PROMPT_EXTRACT

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI  # noqa: F401
except Exception as exc:
    logger.debug("OpenAI import failed: %s", exc)
    OpenAI = None  # type: ignore

try:
    from google import genai  # noqa: F401
except Exception as exc:
    logger.debug("Gemini import failed: %s", exc)
    genai = None  # type: ignore

try:
    import requests
except Exception as exc:
    logger.debug("requests import failed: %s", exc)
    requests = None  # type: ignore


# =========================================================
# Constants
# =========================================================
DEFAULT_TIMEOUT = 180
DEFAULT_RETRIES = 2
MAX_LINE_LENGTH = 800
PROMPT_CLEAN_PREFIX = r"^\s*(here is|here are|output:|result:)\s*"


# =========================================================
# Clean LLM output
# =========================================================
def clean_llm_output(text: Any) -> str:
    """Remove common LLM formatting and noise from output."""
    if text is None:
        return ""

    text = str(text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(PROMPT_CLEAN_PREFIX, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# =========================================================
# Provider helpers
# =========================================================

def _normalize_provider(provider: str) -> str:
    return provider.strip().title() if isinstance(provider, str) else ""


def _fetch_local_response(prompt: str, client: Any, model: str, provider: str) -> str:
    if provider == "Lm Studio":
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return getattr(response.choices[0].message, "content", "") or ""

    if provider == "Ollama":
        if requests is None:
            raise RuntimeError("requests library is required for Ollama provider")

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("response", "") or ""

    raise ValueError(f"Unsupported local provider: {provider}")


def _fetch_cloud_response(prompt: str, client: Any, model: str, provider: str) -> str:
    if provider == "Openai":
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return getattr(response.choices[0].message, "content", "") or ""

    if provider == "Gemini":
        response = client.models.generate_content(model=model, contents=prompt)
        return getattr(response, "text", "") or ""

    if provider == "Anthropic":
        response = client.messages.create(
            model=model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        if getattr(response, "content", None):
            return getattr(response.content[0], "text", "") or ""
        return ""

    raise ValueError(f"Unsupported cloud provider: {provider}")


# =========================================================
# Low-level prompt call
# =========================================================
def perguntar(
    prompt: str,
    client: Any,
    model: str,
    provider: str,
    modo: str,
    cache: Optional[Dict[str, str]] = None,
    retries: int = DEFAULT_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """Send a prompt to the selected LLM provider and return cleaned text."""
    from core.cache import hash_prompt, save_cache

    if not prompt or not isinstance(prompt, str):
        return ""
    if not model:
        return ""

    provider_normalized = _normalize_provider(provider)
    prompt_hash = hash_prompt(prompt)

    if cache is not None and prompt_hash in cache:
        logger.debug("Cache hit for prompt")
        return cache[prompt_hash]

    result_text = ""
    for attempt in range(1, retries + 1):
        try:
            if modo.strip().lower() == "local":
                result_text = _fetch_local_response(prompt, client, model, provider_normalized)
            else:
                result_text = _fetch_cloud_response(prompt, client, model, provider_normalized)

            if result_text:
                break

        except Exception as exc:
            logger.warning("Attempt %s failed for provider %s: %s", attempt, provider_normalized, exc)
            result_text = ""

    result_text = clean_llm_output(result_text)

    if cache is not None and result_text:
        cache[prompt_hash] = result_text
        save_cache(cache)

    return result_text


# =========================================================
# High-level auto cleaner
# =========================================================
# =========================================================
# High-level auto cleaner (adjusted to accept ctx + prompt)
# =========================================================
def perguntar_auto(
    ctx: Dict[str, Any],
    prompt: str,
) -> str:
    """Wrapper universal: recebe ctx + prompt e chama perguntar() corretamente."""
    if not isinstance(ctx, dict):
        raise TypeError("ctx must be a dict")

    client = ctx.get("client")
    model = ctx.get("model", "")
    provider = ctx.get("provider", "")
    modo = ctx.get("modo", "Cloud")
    cache = ctx.get("cache")

    raw = perguntar(prompt, client, model, provider, modo, cache)
    if not raw:
        return ""

    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith(("here", "output", "result")):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if len(line) > MAX_LINE_LENGTH:
            continue
        lines.append(line)

    return "\n".join(lines)



# =========================================================
# Multi-pass requirement extraction
# =========================================================
def perguntar_extract(texto: str, ctx: Dict[str, Any]) -> str:
    """Extract requirements using a multi-pass prompt strategy."""
    if not texto or not isinstance(texto, str):
        return ""
    if not isinstance(ctx, dict):
        raise TypeError("ctx must be a dict")

    base_prompt = f"{PROMPT_EXTRACT}\n{texto}".strip()
    client = ctx.get("client")
    model = ctx.get("model", "")
    provider = ctx.get("provider", "")
    modo = ctx.get("modo", "Cloud")
    cache = ctx.get("cache")

    response_one = perguntar_auto(ctx, base_prompt)
    extra_instruction = "\n\nFind additional requirements that may have been missed."
    response_two = perguntar_auto(ctx, base_prompt + extra_instruction)

    if response_two and response_two != response_one:
        return f"{response_one}\n{response_two}".strip()
    return response_one
    
