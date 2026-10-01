"""End-to-end agent flows through the real local LLM (slow, ~20–90 s per email).

LLM output varies between runs, so these assert facts and structure, never exact wording.
"""
import re

import pytest

from common import phoenix, test_db
from common.test_data import AMIT_HOME_LOAN, RAHUL_BALANCE, RAHUL_SAVINGS_ACCOUNT_NO, RAHUL_SAVINGS_BALANCE, \
    UNREGISTERED_SENDER
from db import repository

pytestmark = pytest.mark.llm


def test_non_account_query_uses_product_agent(dashboard):
    dashboard.open()
    dashboard.open_email(AMIT_HOME_LOAN["id"])
    dashboard.process_email()

    assert not dashboard.has_exception()
    assert dashboard.metric("Intent") == "Non-Account"
    assert dashboard.metric("Authentication") == "N/A"
    steps = dashboard.pipeline_steps()
    assert steps.get("Product Information") == "done"
    assert "Authentication" not in steps and "Core Banking" not in steps
    body = dashboard.draft_body()
    assert body.startswith("Dear Amit")
    assert "Priya Sharma" in body
    dashboard.open_tab("Retrieved data")
    assert "ABC Home Loan" in dashboard.visible_text()


def test_account_query_authenticates_and_uses_core_banking(dashboard):
    dashboard.open()
    dashboard.open_email(RAHUL_BALANCE["id"])
    dashboard.process_email()

    m = dashboard.metrics()
    assert (m["Intent"], m["Sub-intent"], m["Authentication"]) == ("Account", "Balance", "SUCCESS")
    steps = dashboard.pipeline_steps()
    assert steps.get("Authentication") == "done" and steps.get("Core Banking") == "done"
    body = dashboard.draft_body()
    assert RAHUL_SAVINGS_ACCOUNT_NO not in body, "full account number leaked into the draft"
    assert RAHUL_SAVINGS_BALANCE in body, f"balance {RAHUL_SAVINGS_BALANCE} not stated correctly in draft:\n{body}"


def test_unregistered_sender_fails_authentication(dashboard):
    s = UNREGISTERED_SENDER
    new_id = repository.add_email(s["email"], s["name"], s["subject"], s["body"], s["priority"])
    dashboard.open()
    dashboard.open_email(new_id)
    dashboard.process_email()

    assert dashboard.metric("Authentication") == "NOT_FOUND"
    steps = dashboard.pipeline_steps()
    assert steps.get("Authentication") == "fail"
    assert steps.get("Core Banking") == "skip"
    assert not re.search(r"Rs\.?\s?\d", dashboard.draft_body()), "draft discloses an amount to an unverified sender"


def test_run_is_traced_in_phoenix_with_tool_spans(dashboard):
    dashboard.open()
    dashboard.open_email(RAHUL_BALANCE["id"])
    dashboard.process_email()

    trace_id = dashboard.trace_id()
    assert trace_id and trace_id == test_db.latest_response(RAHUL_BALANCE["id"])["trace_id"]
    spans = phoenix.spans_for_trace(trace_id)
    tools = {s["name"] for s in spans if s["span_kind"] == "TOOL"}
    agents = {s["name"] for s in spans if s["span_kind"] == "AGENT"}
    assert {"lookup_customer_by_email", "get_accounts"} <= tools, tools
    assert {"intent_identification_agent", "authentication_agent", "core_banking_agent",
            "email_drafting_agent"} <= agents, agents
