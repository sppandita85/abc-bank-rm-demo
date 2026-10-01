"""LangGraph orchestration of the RM email agents.

START -> intent_identification_agent
           |- non_account -> product_information_agent -> email_drafting_agent -> END
           |- account     -> authentication_agent
                               |- SUCCESS   -> core_banking_agent -> email_drafting_agent -> END
                               |- NOT_FOUND -> email_drafting_agent -> END
"""
from __future__ import annotations

import json
import time
from typing import Callable

from langgraph.graph import END, START, StateGraph
from openinference.instrumentation import using_attributes
from opentelemetry.trace import format_trace_id

from agents.auth_agent import authentication_agent, route_after_auth
from agents.core_banking_agent import core_banking_agent
from agents.email_drafting_agent import email_drafting_agent
from agents.intent_agent import intent_identification_agent, route_after_intent
from agents.product_agent import product_information_agent
from agents.state import AgentState
from db import repository
from observability.tracing import get_tracer, init_tracing

AGENT_ORDER = ["intent_identification_agent", "authentication_agent", "product_information_agent",
               "core_banking_agent", "email_drafting_agent"]


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("intent_identification_agent", intent_identification_agent)
    g.add_node("authentication_agent", authentication_agent)
    g.add_node("product_information_agent", product_information_agent)
    g.add_node("core_banking_agent", core_banking_agent)
    g.add_node("email_drafting_agent", email_drafting_agent)

    g.add_edge(START, "intent_identification_agent")
    g.add_conditional_edges("intent_identification_agent", route_after_intent,
                            ["authentication_agent", "product_information_agent"])
    g.add_conditional_edges("authentication_agent", route_after_auth,
                            ["core_banking_agent", "email_drafting_agent"])
    g.add_edge("product_information_agent", "email_drafting_agent")
    g.add_edge("core_banking_agent", "email_drafting_agent")
    g.add_edge("email_drafting_agent", END)
    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        init_tracing()
        _graph = build_graph()
    return _graph


def process_email(email_id: int, on_step: Callable[[str, dict], None] | None = None) -> dict:
    """Run the agent pipeline for one email, persist the draft and return the final state."""
    graph = get_graph()
    email = repository.get_email(email_id)
    if not email:
        raise ValueError(f"Email {email_id} not found")

    start = time.perf_counter()
    state: dict = {"email": email, "agent_trace": []}
    with using_attributes(session_id=f"email-{email_id}", user_id=email["from_email"],
                          metadata={"email_id": email_id, "subject": email["subject"]},
                          tags=["rm-assistant"]):
        with get_tracer().start_as_current_span("rm_email_pipeline") as root:
            root.set_attribute("openinference.span.kind", "CHAIN")
            root.set_attribute("input.value", f"{email['subject']}\n\n{email['body']}")
            trace_id = format_trace_id(root.get_span_context().trace_id)

            for update in graph.stream({"email": email, "agent_trace": []}, stream_mode="updates"):
                for node, delta in update.items():
                    delta = delta or {}
                    for k, v in delta.items():
                        state[k] = state.get(k, []) + v if k == "agent_trace" else v
                    if on_step:
                        on_step(node, delta)

            root.set_attribute("output.value", json.dumps(
                {"intent": state.get("intent"), "subject": state.get("draft_subject"),
                 "body": state.get("draft_body")}))
            root.set_attribute("rm.intent", state.get("intent", ""))
            root.set_attribute("rm.data_source", state.get("data_source", ""))

    state["processing_ms"] = int((time.perf_counter() - start) * 1000)
    state["trace_id"] = trace_id
    state["response_id"] = repository.save_draft(email_id, state)
    return state


if __name__ == "__main__":
    import sys

    result = process_email(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    for step in result["agent_trace"]:
        print(f"[{step['agent']}] {step['summary']} ({step['duration_ms']} ms)")
    print("\nSUBJECT:", result["draft_subject"])
    print(result["draft_body"])
    print("\nRM NOTES:", result.get("internal_notes"))
    print("\ntrace_id:", result["trace_id"])
    from opentelemetry import trace
    trace.get_tracer_provider().force_flush()
