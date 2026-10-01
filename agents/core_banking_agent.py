"""core_banking_agent – fetches the authenticated customer's data from core banking tables.

Only fixed, parameterised tools are called; the LLM never writes SQL.
"""
from __future__ import annotations

import time
from datetime import datetime

from agents.state import AgentState
from agents.tools import get_accounts, get_cards, get_fixed_deposits, get_loans, get_recent_transactions

TOOLS = {
    "accounts": get_accounts,
    "recent_transactions": get_recent_transactions,
    "loans": get_loans,
    "cards": get_cards,
    "fixed_deposits": get_fixed_deposits,
}

# which data sets each sub-intent needs
PLAN = {
    "balance": ["accounts"],
    "transactions": ["accounts", "recent_transactions"],
    "dispute": ["accounts", "recent_transactions"],
    "loan": ["loans"],
    "card": ["cards"],
    "fixed_deposit": ["fixed_deposits"],
    "account_summary": ["accounts", "loans", "cards", "fixed_deposits"],
}


def _find_duplicate_debits(txns: list[dict]) -> list[dict]:
    """Flag same-amount, same-merchant debits within 10 minutes (possible double debit)."""
    dupes = []
    debits = [t for t in txns if t["dr_cr"] == "DR"]
    for i, a in enumerate(debits):
        for b in debits[i + 1:]:
            if a["description"] == b["description"] and a["amount"] == b["amount"]:
                gap = abs((datetime.fromisoformat(a["txn_date"]) - datetime.fromisoformat(b["txn_date"])).total_seconds())
                if gap <= 600:
                    dupes.append({"description": a["description"], "amount": a["amount"],
                                  "references": [a["reference_no"], b["reference_no"]],
                                  "dates": [b["txn_date"], a["txn_date"]]})
    return dupes


def core_banking_agent(state: AgentState) -> dict:
    start = time.perf_counter()
    cid = state["customer_id"]
    sub_intent = state.get("sub_intent", "account_summary")
    datasets = PLAN.get(sub_intent, PLAN["account_summary"])

    data: dict = {}
    for name in datasets:
        args = {"customer_id": cid}
        if name == "recent_transactions":
            args["limit"] = 15 if sub_intent == "dispute" else 10
        data[name] = TOOLS[name].invoke(args)

    if sub_intent == "dispute":
        data["suspected_duplicate_debits"] = _find_duplicate_debits(data.get("recent_transactions", []))

    counts = {k: len(v) for k, v in data.items()}
    return {
        "retrieved_data": data,
        "data_source": "core_banking",
        "agent_trace": [{
            "agent": "core_banking_agent",
            "status": "completed",
            "summary": "Fetched " + ", ".join(f"{k} ({n})" for k, n in counts.items()),
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "output": {"customer_id": cid, "datasets": counts,
                       "tools": [TOOLS[n].name for n in datasets]},
        }],
    }
