"""email_drafting_agent – composes the reply for RM approval from retrieved data."""
from __future__ import annotations

import json
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage

import config
from agents.llm import get_llm, parse_json
from agents.state import AgentState

SYSTEM_PROMPT = f"""You are the Email Drafting Agent for {config.BANK_NAME}. You draft replies that a
Relationship Manager ({config.RM_NAME}, {config.RM_TITLE}) will review before sending.

Rules:
- Use ONLY facts present in RETRIEVED DATA. Never invent numbers, rates, dates or policies.
  If something asked is not in the data, say the RM will confirm it separately.
- Never promise timelines, refunds, approvals or waivers.
- ONLY when sub_intent is "dispute" (a complaint about a wrong/duplicate debit), acknowledge the facts
  found and say the matter has been raised with the concerned team for review. Do not add this line otherwise.
- Amounts in Indian Rupees formatted like "Rs 1,23,456.78". Dates like "12 Oct 2026".
- Account numbers are already masked - keep them masked. Never reveal full account numbers.
- Warm, professional, concise tone. Use short paragraphs separated by a blank line, and bullet points ("- ") for figures.
- Address the customer by first name. Close with:
  "Warm regards,\\n{config.RM_NAME}\\n{config.RM_TITLE}\\n{config.BANK_NAME}"
- internal_notes: 1-3 short action items for the RM only (e.g. raise dispute ticket), not sent to customer.

Respond ONLY with JSON: {{"subject": "...", "body": "...", "internal_notes": "..."}}"""


def _mask(value: str) -> str:
    return re.sub(r"\b(\d{6,})(\d{4})\b", lambda m: "X" * len(m.group(1)) + m.group(2), value)


def _context(state: AgentState) -> str:
    if state.get("data_source") in ("core_banking", "product_information"):
        return _mask(json.dumps(state.get("retrieved_data", {}), indent=1, default=str))
    return json.dumps({"note": "Sender could not be authenticated as a registered customer. Do not share "
                               "any account information. Politely ask them to write from their registered "
                               "email address or call the branch to verify identity."})


def _fallback(state: AgentState) -> dict:
    first = (state["email"].get("from_name") or "Customer").split()[0]
    return {
        "subject": f"Re: {state['email']['subject']}",
        "body": (f"Dear {first},\n\nThank you for writing to us. I have received your request and am reviewing "
                 f"the details. I will get back to you shortly with a complete response.\n\n"
                 f"Warm regards,\n{config.RM_NAME}\n{config.RM_TITLE}\n{config.BANK_NAME}"),
        "internal_notes": "LLM drafting failed - holding reply generated. Please complete manually.",
    }


def email_drafting_agent(state: AgentState) -> dict:
    start = time.perf_counter()
    email = state["email"]
    customer = state.get("customer") or {}
    user_msg = (
        f"CUSTOMER EMAIL\nFrom: {email['from_name']} <{email['from_email']}>\n"
        f"Subject: {email['subject']}\n\n{email['body']}\n\n"
        f"CLASSIFICATION: intent={state.get('intent')}, sub_intent={state.get('sub_intent')}\n"
        f"CUSTOMER PROFILE: {json.dumps({k: customer.get(k) for k in ('full_name', 'segment', 'city')}) if customer else 'Prospect / not an existing customer'}\n\n"
        f"RETRIEVED DATA (source={state.get('data_source', 'none')}):\n{_context(state)}"
    )
    try:
        resp = get_llm(json_mode=True, temperature=0.2).invoke([SystemMessage(SYSTEM_PROMPT), HumanMessage(user_msg)])
        draft = parse_json(resp.content)
        if not draft.get("body"):
            raise ValueError("empty body")
        method = "llm"
    except Exception as exc:
        draft = _fallback(state)
        draft["internal_notes"] += f" ({type(exc).__name__})"
        method = "fallback"

    body = _mask(str(draft["body"]).replace("\\n", "\n"))
    notes = draft.get("internal_notes") or ""
    if isinstance(notes, list):
        notes = "\n".join(f"- {n}" for n in notes)
    return {
        "draft_subject": draft.get("subject") or f"Re: {email['subject']}",
        "draft_body": body,
        "internal_notes": str(notes),
        "data_source": state.get("data_source") or "none",
        "agent_trace": [{
            "agent": "email_drafting_agent",
            "status": "completed",
            "summary": f"Draft ready ({len(body.split())} words, via {method})",
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "output": {"subject": draft.get("subject"), "method": method},
        }],
    }
