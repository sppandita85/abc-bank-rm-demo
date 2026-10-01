"""authentication_agent – pass-through for now.

Resolves the sender to a customer record by registered email and approves. `verify()` is the
extension point for real checks (OTP, device binding, KBA, etc.).
"""
from __future__ import annotations

import time

from agents.state import AgentState
from agents.tools import lookup_customer_by_email


def verify(customer: dict, email: dict) -> bool:
    """Pass-through: any sender matching a registered customer email is authenticated."""
    return True


def authentication_agent(state: AgentState) -> dict:
    start = time.perf_counter()
    email = state["email"]
    customer = lookup_customer_by_email.invoke({"email": email["from_email"]})

    if customer and verify(customer, email):
        status, summary = "SUCCESS", f"Authenticated {customer['full_name']} ({customer['customer_id']})"
    else:
        status, summary = "NOT_FOUND", f"{email['from_email']} is not a registered customer email"

    return {
        "customer": customer,
        "customer_id": customer["customer_id"] if customer else None,
        "auth_status": status,
        "agent_trace": [{
            "agent": "authentication_agent",
            "status": "completed" if status == "SUCCESS" else "failed",
            "summary": summary,
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "output": {"auth_status": status, "customer_id": customer and customer["customer_id"],
                       "tools": ["lookup_customer_by_email"]},
        }],
    }


def route_after_auth(state: AgentState) -> str:
    return "core_banking_agent" if state["auth_status"] == "SUCCESS" else "email_drafting_agent"
