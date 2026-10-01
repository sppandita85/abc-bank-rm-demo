import pytest

pytestmark = pytest.mark.smoke


def test_dashboard_loads(dashboard):
    dashboard.open()

    assert "ABC Bank" in dashboard.header_text()
    assert "RM Assistant" in dashboard.header_text()
    assert dashboard.kpi("New queries") == "15"
    assert dashboard.kpi("Pending review") == "0"
    assert dashboard.kpi("Approved") == "0"
    assert dashboard.kpi("Rejected") == "0"
    assert any("Inbox" in t for t in dashboard.tab_names())
    assert any("Activity history" in t for t in dashboard.tab_names())
    assert not dashboard.has_exception()


def test_system_health_all_green(dashboard):
    dashboard.open()

    health = dashboard.health()
    assert len(health) == 3, health
    assert all(health.values()), f"Unhealthy services: {health}"
