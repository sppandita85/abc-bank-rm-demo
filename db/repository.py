"""Data access for the RM workflow (emails, drafts, RM decisions)."""
from __future__ import annotations

import json

from db.connection import execute, fetch_all, fetch_one


def list_emails(status: str | None = None) -> list[dict]:
    sql = """SELECT e.*, r.intent, r.sub_intent
             FROM emails e
             LEFT JOIN LATERAL (SELECT intent, sub_intent FROM email_responses
                                WHERE email_id = e.email_id ORDER BY response_id DESC LIMIT 1) r ON TRUE"""
    if status:
        return fetch_all(sql + " WHERE e.status = %s ORDER BY e.received_at DESC", (status,))
    return fetch_all(sql + " ORDER BY e.received_at DESC")


def get_email(email_id: int) -> dict | None:
    return fetch_one("SELECT * FROM emails WHERE email_id = %s", (email_id,))


def add_email(from_email: str, from_name: str, subject: str, body: str, priority: str = "NORMAL") -> int:
    row = execute("""INSERT INTO emails (from_email, from_name, subject, body, priority)
                     VALUES (%s, %s, %s, %s, %s) RETURNING email_id""",
                  (from_email, from_name, subject, body, priority))
    return row["email_id"]


def save_draft(email_id: int, state: dict) -> int:
    row = execute(
        """INSERT INTO email_responses (email_id, intent, sub_intent, confidence, customer_id, auth_status,
               data_source, retrieved_data, draft_subject, draft_body, internal_notes, agent_trace, trace_id, processing_ms)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING response_id""",
        (email_id, state.get("intent"), state.get("sub_intent"), state.get("confidence"),
         state.get("customer_id"), state.get("auth_status", "N/A"), state.get("data_source"),
         json.dumps(state.get("retrieved_data", {}), default=str), state.get("draft_subject"),
         state.get("draft_body"), state.get("internal_notes"),
         json.dumps(state.get("agent_trace", []), default=str), state.get("trace_id"),
         state.get("processing_ms")))
    execute("UPDATE emails SET status = 'PENDING_REVIEW' WHERE email_id = %s", (email_id,))
    return row["response_id"]


def latest_response(email_id: int) -> dict | None:
    return fetch_one("SELECT * FROM email_responses WHERE email_id = %s ORDER BY response_id DESC LIMIT 1",
                     (email_id,))


def record_action(response_id: int, action: str, final_subject: str | None, final_body: str | None,
                  comment: str | None) -> None:
    """action: ACCEPTED | ACCEPTED_WITH_EDITS | REJECTED"""
    execute("""UPDATE email_responses SET rm_action = %s, final_subject = %s, final_body = %s,
                      rm_comment = %s, actioned_at = now()
               WHERE response_id = %s""", (action, final_subject, final_body, comment, response_id))
    status = "REJECTED" if action == "REJECTED" else "APPROVED"
    execute("""UPDATE emails SET status = %s
               WHERE email_id = (SELECT email_id FROM email_responses WHERE response_id = %s)""",
            (status, response_id))


def kpis() -> dict:
    return fetch_one("""
        SELECT count(*) FILTER (WHERE status = 'NEW')            AS new,
               count(*) FILTER (WHERE status = 'PENDING_REVIEW') AS pending_review,
               count(*) FILTER (WHERE status = 'APPROVED')       AS approved,
               count(*) FILTER (WHERE status = 'REJECTED')       AS rejected,
               (SELECT round(avg(processing_ms) / 1000.0, 1) FROM email_responses) AS avg_secs,
               (SELECT count(*) FROM email_responses WHERE rm_action = 'ACCEPTED_WITH_EDITS') AS edited
        FROM emails""")


def history() -> list[dict]:
    return fetch_all("""
        SELECT r.response_id, e.email_id, e.from_name, e.subject, r.intent, r.sub_intent, r.data_source,
               r.rm_action, r.processing_ms, r.created_at, r.actioned_at, r.trace_id
        FROM email_responses r JOIN emails e USING (email_id)
        ORDER BY r.response_id DESC""")
