"""Selenium fixtures: a fresh Chrome per test (Selenium Manager resolves chromedriver automatically)."""
from pathlib import Path

import pytest
from selenium import webdriver

from selenium_tests.pages.dashboard import DashboardPage

SCREENSHOT_DIR = Path(__file__).resolve().parents[1] / "reports" / "selenium"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture
def driver(request):
    options = webdriver.ChromeOptions()
    # --headed is provided by pytest-playwright and shared by both suites
    if not request.config.getoption("--headed"):
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,1000")
    drv = webdriver.Chrome(options=options)
    yield drv
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        drv.save_screenshot(str(SCREENSHOT_DIR / f"{request.node.name}.png"))
    drv.quit()


@pytest.fixture
def dashboard(driver, app_url) -> DashboardPage:
    return DashboardPage(driver, app_url)
