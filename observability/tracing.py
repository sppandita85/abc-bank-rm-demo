"""Arize Phoenix / OpenTelemetry setup.

`init_tracing()` registers an OTLP exporter pointed at the local Phoenix container and
auto-instruments LangChain/LangGraph: every agent node, every ChatOllama call and every database
tool (agents/tools.py) becomes a span.
"""
from __future__ import annotations

import requests
from opentelemetry import trace

import config

_initialised = False
_TRACER_NAME = "abc-bank-rm"


def init_tracing() -> None:
    global _initialised
    if _initialised:
        return
    from phoenix.otel import register
    from openinference.instrumentation.langchain import LangChainInstrumentor

    provider = register(
        project_name=config.PHOENIX_PROJECT,
        endpoint=config.PHOENIX_COLLECTOR_ENDPOINT,
        batch=True,
        set_global_tracer_provider=True,
        verbose=False,
    )
    LangChainInstrumentor().instrument(tracer_provider=provider)
    _initialised = True


def get_tracer():
    return trace.get_tracer(_TRACER_NAME)


def phoenix_trace_url(trace_id: str | None) -> str:
    """Best-effort deep link to a trace in the Phoenix UI."""
    base = config.PHOENIX_UI_URL.rstrip("/")
    try:
        resp = requests.get(f"{base}/v1/projects", timeout=2)
        for p in resp.json().get("data", []):
            if p.get("name") == config.PHOENIX_PROJECT:
                url = f"{base}/projects/{p['id']}"
                return f"{url}/traces/{trace_id}" if trace_id else url
    except Exception:
        pass
    return base


def phoenix_up() -> bool:
    try:
        return requests.get(config.PHOENIX_UI_URL, timeout=2).ok
    except Exception:
        return False
