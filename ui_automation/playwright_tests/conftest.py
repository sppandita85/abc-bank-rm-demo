"""Playwright fixtures. pytest-playwright provides `page` and the CLI options
(--headed, --browser, --tracing, --screenshot, --video, --output)."""
import pytest

from playwright_tests.pages.dashboard import DashboardPage


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1600, "height": 1000}}


@pytest.fixture
def dashboard(page, app_url) -> DashboardPage:
    return DashboardPage(page, app_url)
