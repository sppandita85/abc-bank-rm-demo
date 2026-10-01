"""intent_identification_agent – classifies an incoming RM email."""
from __future__ import annotations

import time

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm, parse_json
from agents.state import AgentState

ACCOUNT_SUB_INTENTS = ["balance", "transactions", "dispute", "loan", "card", "fixed_deposit", "account_summary"]
PRODUCT_CATEGORIES = ["SAVINGS", "CURRENT", "FD", "HOME_LOAN", "PERSONAL_LOAN", "CAR_LOAN",
                      "CREDIT_CARD", "INVESTMENT", "SERVICES"]

SYSTEM_PROMPT = f"""You are the Intent Identification Agent for ABC Bank's Relationship Manager desk.
Classify the customer's email.

intent:
- "account": the customer asks about THEIR OWN existing relationship - their balance, their
  transactions, a debit/refund dispute, their loan outstanding/EMI, their card status/dues,
  their fixed deposit maturity, or a summary of their holdings. Needs customer data.
- "non_account": a general enquiry about products, rates, fees, eligibility, documents or
  features that can be answered from the product catalogue without the customer's data.

sub_intent (for account): one of {ACCOUNT_SUB_INTENTS}
sub_intent (for non_account): "product_info"
product_category: one of {PRODUCT_CATEGORIES} most relevant to the email (or null).

Rule of thumb: if answering needs ANY figure or status specific to the sender's own holdings
(my balance, my FD maturity date/amount, my EMI, my outstanding, my card status), it is "account",
even if the email also asks about options or products.

Examples:
- "What is the current balance in my savings account?" -> account / balance
- "My FD is maturing this month, confirm the maturity amount and can I renew?" -> account / fixed_deposit
- "How much is outstanding on my personal loan and what are foreclosure charges?" -> account / loan
- "Rs 5,000 was debited twice from my account" -> account / dispute
- "Why was my credit card declined?" -> account / card
- "What are your FD rates for senior citizens?" -> non_account / product_info / FD
- "Which credit card is best for travel?" -> non_account / product_info / CREDIT_CARD
- "Documents needed to open a current account for my company" -> non_account / product_info / CURRENT

Respond ONLY with JSON:
{{"intent": "...", "sub_intent": "...", "product_category": "... or null", "confidence": 0.0-1.0,
  "entities": {{"account_number": "... or null", "product_name": "... or null"}},
  "reasoning": "one short sentence"}}"""

_ACCOUNT_KEYWORDS = {
    "balance": ["balance"],
    "transactions": ["transactions", "statement", "last 10"],
    "dispute": ["debited twice", "refund", "duplicate", "wrongly debited", "dispute"],
    "loan": ["my loan", "emi", "outstanding", "foreclos"],
    "card": ["my card", "blocked", "declined", "due date"],
    "fixed_deposit": ["my fd", "fixed deposit is maturing", "maturity", "my fixed deposit"],
}


def _heuristic(text: str) -> dict:
    t = text.lower()
    for sub, words in _ACCOUNT_KEYWORDS.items():
        if any(w in t for w in words):
            return {"intent": "account", "sub_intent": sub, "product_category": None,
                    "confidence": 0.5, "entities": {}, "reasoning": "Keyword fallback"}
    return {"intent": "non_account", "sub_intent": "product_info", "product_category": None,
            "confidence": 0.5, "entities": {}, "reasoning": "Keyword fallback"}


def intent_identification_agent(state: AgentState) -> dict:
    start = time.perf_counter()
    email = state["email"]
    user_msg = f"From: {email['from_name']} <{email['from_email']}>\nSubject: {email['subject']}\n\n{email['body']}"
    try:
        resp = get_llm(json_mode=True).invoke([SystemMessage(SYSTEM_PROMPT), HumanMessage(user_msg)])
        result = parse_json(resp.content)
        if result.get("intent") not in ("account", "non_account"):
            raise ValueError(f"bad intent {result.get('intent')}")
        method = "llm"
    except Exception as exc:  # LLM unavailable or malformed output
        result = _heuristic(f"{email['subject']} {email['body']}")
        result["reasoning"] += f" ({type(exc).__name__})"
        method = "heuristic"

    if result["intent"] == "non_account":
        result["sub_intent"] = "product_info"
    elif result.get("sub_intent") not in ACCOUNT_SUB_INTENTS:
        result["sub_intent"] = "account_summary"
    category = result.get("product_category")
    if category not in PRODUCT_CATEGORIES:
        category = None

    return {
        "intent": result["intent"],
        "sub_intent": result["sub_intent"],
        "product_category": category,
        "confidence": float(result.get("confidence") or 0.0),
        "entities": result.get("entities") or {},
        "reasoning": result.get("reasoning", ""),
        "agent_trace": [{
            "agent": "intent_identification_agent",
            "status": "completed",
            "summary": f"{result['intent']} / {result['sub_intent']}"
                       + (f" / {category}" if category else "") + f" (via {method})",
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "output": {**result, "product_category": category, "method": method},
        }],
    }


def route_after_intent(state: AgentState) -> str:
    return "authentication_agent" if state["intent"] == "account" else "product_information_agent"
