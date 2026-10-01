"""RM decisions on AI drafts. Drafts are seeded directly in the DB, so these tests don't need the LLM."""
import pytest

from common import test_db
from common.test_data import AMIT_HOME_LOAN, ANANYA_DISPUTE, RAHUL_BALANCE
from db import repository

pytestmark = pytest.mark.actions

PS_LINE = "P.S. I will call you this afternoon regarding the payment."


def test_accept_draft_as_is(dashboard):
    test_db.seed_draft(AMIT_HOME_LOAN["id"], intent="non_account")
    dashboard.open()
    dashboard.open_email(AMIT_HOME_LOAN["id"])
    assert dashboard.kpi("Pending review") == "1"

    dashboard.accept()

    assert any(a.startswith("Accepted by") for a in dashboard.alert_texts())
    assert dashboard.reprocess_button_visible()
    assert dashboard.kpi("Approved") == "1"
    resp = test_db.latest_response(AMIT_HOME_LOAN["id"])
    assert resp["rm_action"] == "ACCEPTED"
    assert resp["final_body"] == resp["draft_body"]
    assert test_db.email_row(AMIT_HOME_LOAN["id"])["status"] == "APPROVED"


def test_accept_with_edits(dashboard):
    test_db.seed_draft(RAHUL_BALANCE["id"])
    dashboard.open()
    dashboard.open_email(RAHUL_BALANCE["id"])

    assert dashboard.button_enabled("accept")
    assert not dashboard.button_enabled("edit")

    dashboard.edit_body("\n\n" + PS_LINE)

    assert not dashboard.button_enabled("accept")
    assert dashboard.button_enabled("edit")
    assert "You have edited the draft" in dashboard.visible_text()

    dashboard.accept_with_edits()

    assert any(a.startswith("Accepted With Edits") for a in dashboard.alert_texts())
    assert PS_LINE in dashboard.draft_body()
    assert "View original AI draft" in dashboard.expander_titles()
    assert dashboard.kpi("Approved") == "1"
    resp = test_db.latest_response(RAHUL_BALANCE["id"])
    assert resp["rm_action"] == "ACCEPTED_WITH_EDITS"
    assert PS_LINE in resp["final_body"] and PS_LINE not in resp["draft_body"]


def test_reject_requires_comment(dashboard):
    test_db.seed_draft(ANANYA_DISPUTE["id"])
    dashboard.open()
    dashboard.open_email(ANANYA_DISPUTE["id"])

    dashboard.reject("")
    assert "Please add a comment explaining the rejection." in dashboard.alert_texts()
    assert test_db.email_row(ANANYA_DISPUTE["id"])["status"] == "PENDING_REVIEW"

    comment = "Please include the transaction reference numbers"
    dashboard.reject(comment)

    assert any(a.startswith("Rejected by") and comment in a for a in dashboard.alert_texts())
    assert dashboard.reprocess_button_visible()
    assert dashboard.kpi("Rejected") == "1"
    resp = test_db.latest_response(ANANYA_DISPUTE["id"])
    assert resp["rm_action"] == "REJECTED" and resp["rm_comment"] == comment


def test_activity_history_counts(dashboard):
    accepted = test_db.seed_draft(AMIT_HOME_LOAN["id"], intent="non_account")
    test_db.seed_draft(RAHUL_BALANCE["id"])
    repository.record_action(accepted, "ACCEPTED", None, "ok", None)
    dashboard.open()

    dashboard.open_tab("Activity history")

    m = dashboard.metrics()
    assert m["Drafts generated"] == "2"
    assert m["Account queries"] == "1"
    assert m["Acceptance rate"] == "100%"
