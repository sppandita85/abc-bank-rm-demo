"""Test database helpers: reset, seed AI drafts without the LLM, and read back results."""
from __future__ import annotations

import config
from db import init_db, repository
from db.connection import fetch_one

DEMO_DB = "abc_bank_rm"


def _guard() -> None:
    if config.PG_DB == DEMO_DB:
        raise RuntimeError(f"Refusing to reset the demo database '{DEMO_DB}'. "
                           "UI tests must run against the test database (see ui_automation/conftest.py).")


def reset_db() -> None:
    """Recreate schema and seed data in the test database (15 NEW emails)."""
    _guard()
    init_db.main()


# canned agent output per email, so RM-action tests don't depend on the LLM
_SEEDS = {
    "account": {
        "intent": "account", "sub_intent": "balance", "auth_status": "SUCCESS", "data_source": "core_banking",
        "agents": ["intent_identification_agent", "authentication_agent", "core_banking_agent", "email_drafting_agent"],
    },
    "non_account": {
        "intent": "non_account", "sub_intent": "product_info", "auth_status": "N/A",
        "data_source": "product_information",
        "agents": ["intent_identification_agent", "product_information_agent", "email_drafting_agent"],
    },
}


def seed_draft(email_id: int, intent: str = "account", subject: str | None = None, body: str | None = None,
               notes: str = "Seeded draft for UI tests") -> int:
    """Insert an AI draft for `email_id` (email moves to PENDING_REVIEW); returns response_id."""
    _guard()
    email = repository.get_email(email_id)
    seed = _SEEDS[intent]
    first_name = (email["from_name"] or "Customer").split()[0]
    state = {
        "intent": seed["intent"], "sub_intent": seed["sub_intent"], "confidence": 0.95,
        "customer_id": "C1001" if intent == "account" else None, "auth_status": seed["auth_status"],
        "data_source": seed["data_source"], "retrieved_data": {},
        "draft_subject": subject or f"Re: {email['subject']}",
        "draft_body": body or (f"Dear {first_name},\n\nThank you for your email. This is a seeded test draft.\n\n"
                               f"Warm regards,\n{config.RM_NAME}\n{config.RM_TITLE}\n{config.BANK_NAME}"),
        "internal_notes": notes,
        "agent_trace": [{"agent": a, "status": "completed", "summary": "seeded", "duration_ms": 1, "output": {}}
                        for a in seed["agents"]],
        "trace_id": "0" * 32, "processing_ms": 1500,
    }
    return repository.save_draft(email_id, state)


def email_row(email_id: int) -> dict | None:
    return repository.get_email(email_id)


def latest_response(email_id: int) -> dict | None:
    return repository.latest_response(email_id)


def email_count() -> int:
    return fetch_one("SELECT count(*) AS n FROM emails")["n"]
