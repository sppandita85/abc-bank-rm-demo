import pytest

from common import test_db
from common.test_data import AMIT_HOME_LOAN, NEWEST_EMAIL_ID, SEEDED_EMAIL_COUNT, UNREGISTERED_SENDER

pytestmark = pytest.mark.smoke


def test_inbox_lists_all_emails_newest_first(dashboard):
    dashboard.open()

    assert dashboard.inbox_count() == SEEDED_EMAIL_COUNT
    ids = dashboard.inbox_ids()
    assert len(ids) == SEEDED_EMAIL_COUNT
    assert ids[0] == NEWEST_EMAIL_ID


def test_open_email_shows_detail_and_process_button(dashboard):
    dashboard.open()
    dashboard.open_email(AMIT_HOME_LOAN["id"])

    assert AMIT_HOME_LOAN["email"] in dashboard.email_header()
    assert "90 lakh" in dashboard.email_body()
    assert dashboard.process_button_visible()
    assert dashboard.open_button_label(AMIT_HOME_LOAN["id"]) == "Viewing"


def test_status_filter(dashboard):
    dashboard.open()

    dashboard.set_filter("Approved")
    assert dashboard.inbox_count() == 0

    dashboard.set_filter("All")
    assert dashboard.inbox_count() == SEEDED_EMAIL_COUNT


def test_simulated_email_arrives_in_inbox(dashboard):
    dashboard.open()
    s = UNREGISTERED_SENDER
    dashboard.simulate_email(s["name"], s["email"], s["subject"], s["body"], s["priority"])

    new_id = SEEDED_EMAIL_COUNT + 1
    assert dashboard.inbox_ids()[0] == new_id
    assert dashboard.kpi("New queries") == str(SEEDED_EMAIL_COUNT + 1)
    row = test_db.email_row(new_id)
    assert row["from_email"] == s["email"] and row["priority"] == "HIGH" and row["status"] == "NEW"
