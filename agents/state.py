"""Shared LangGraph state passed between agents."""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    email: dict                      # row from `emails`
    intent: str                      # account | non_account
    sub_intent: str
    product_category: str | None
    confidence: float
    entities: dict
    reasoning: str
    customer: dict | None
    customer_id: str | None
    auth_status: str                 # SUCCESS | NOT_FOUND
    retrieved_data: dict[str, Any]
    data_source: str                 # core_banking | product_information | none
    draft_subject: str
    draft_body: str
    internal_notes: str
    # each agent appends one entry: {"agent", "status", "summary", "duration_ms", "output"}
    agent_trace: Annotated[list[dict], operator.add]
