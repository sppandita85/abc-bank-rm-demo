"""Read spans back from Phoenix to check that a UI run was traced."""
from __future__ import annotations

import time

import requests

import config


def spans_for_trace(trace_id: str, timeout: float = 20) -> list[dict]:
    """Poll Phoenix until spans for `trace_id` arrive (spans are exported in batches)."""
    url = f"{config.PHOENIX_UI_URL.rstrip('/')}/v1/projects/{config.PHOENIX_PROJECT}/spans"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url, params={"limit": 500}, timeout=5)
        if resp.ok:
            spans = [s for s in resp.json().get("data", []) if s["context"]["trace_id"] == trace_id]
            if spans:
                return spans
        time.sleep(2)
    return []
