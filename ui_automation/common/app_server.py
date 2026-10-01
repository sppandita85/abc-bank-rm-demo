"""Starts a dedicated Streamlit instance of the app for UI tests.

The instance uses the test database and Phoenix project from the environment (set in conftest.py),
so the demo app on port 8502 and its data are never touched.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _healthy(url: str) -> bool:
    try:
        return requests.get(f"{url}/_stcore/health", timeout=1).text.strip() == "ok"
    except requests.RequestException:
        return False


class AppServer:
    def __init__(self, port: int):
        self.port = port
        self.url = f"http://localhost:{port}"
        self._proc: subprocess.Popen | None = None
        self._log = None

    def start(self, timeout: float = 60) -> str:
        if _healthy(self.url):
            raise RuntimeError(
                f"Port {self.port} is already serving an app. Stop it, set UI_TEST_PORT to a free port, "
                f"or set UI_BASE_URL to test an already running instance.")
        REPORTS_DIR.mkdir(exist_ok=True)
        self._log = open(REPORTS_DIR / "test_app_server.log", "w")
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(self.port),
             "--server.headless", "true"],
            cwd=PROJECT_ROOT, env=os.environ.copy(), stdout=self._log, stderr=subprocess.STDOUT)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._proc.poll() is not None:
                raise RuntimeError(f"Test app exited early; see {REPORTS_DIR / 'test_app_server.log'}")
            if _healthy(self.url):
                return self.url
            time.sleep(0.5)
        self.stop()
        raise RuntimeError(f"Test app did not become healthy on {self.url} within {timeout}s")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        if self._log:
            self._log.close()
