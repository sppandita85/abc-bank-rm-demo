"""Local LLM (Ollama) helpers."""
from __future__ import annotations

import json
import re

import requests
from langchain_ollama import ChatOllama

import config


def get_llm(json_mode: bool = False, temperature: float = 0.0) -> ChatOllama:
    return ChatOllama(
        model=config.OLLAMA_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=temperature,
        format="json" if json_mode else None,
        num_ctx=8192,
    )


def parse_json(text: str) -> dict:
    """Parse model output as JSON, tolerating code fences / surrounding prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def ollama_up() -> bool:
    try:
        tags = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=2).json()
        return any(m["name"] == config.OLLAMA_MODEL for m in tags.get("models", []))
    except Exception:
        return False
