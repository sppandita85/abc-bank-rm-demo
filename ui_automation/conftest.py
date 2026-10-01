"""Shared fixtures for the Selenium and Playwright suites.

The test environment is set BEFORE any app module (config, db, ...) is imported, so both this
process and the Streamlit test server use the test database and Phoenix project.
"""
import os

os.environ["PG_DB"] = os.getenv("UI_TEST_PG_DB", "abc_bank_rm_test")
os.environ["PHOENIX_PROJECT"] = os.getenv("UI_TEST_PHOENIX_PROJECT", "abc-bank-rm-tests")

import pytest  # noqa: E402

from agents.llm import ollama_up  # noqa: E402
from common import test_db  # noqa: E402
from common.app_server import AppServer  # noqa: E402

TEST_PORT = int(os.getenv("UI_TEST_PORT", "8503"))


@pytest.fixture(scope="session")
def app_url():
    """URL of the app under test. Starts a dedicated instance unless UI_BASE_URL is given."""
    test_db.reset_db()
    if os.getenv("UI_BASE_URL"):
        yield os.environ["UI_BASE_URL"].rstrip("/")
        return
    server = AppServer(TEST_PORT)
    yield server.start()
    server.stop()


@pytest.fixture(scope="session")
def base_url(app_url):
    """Overrides pytest-base-url so Playwright's page.goto('/') targets the test app."""
    return app_url


@pytest.fixture(autouse=True)
def fresh_db(app_url):
    """Every test starts from the seeded state: 15 NEW emails, no drafts."""
    test_db.reset_db()
    yield


def pytest_collection_modifyitems(config, items):
    if any(item.get_closest_marker("llm") for item in items) and not ollama_up():
        skip = pytest.mark.skip(reason="Ollama / llama3.1 not reachable – LLM tests skipped")
        for item in items:
            if item.get_closest_marker("llm"):
                item.add_marker(skip)
