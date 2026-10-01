"""Page Object for the RM Assistant dashboard – Selenium WebDriver implementation.

Selectors rely on Streamlit's stable hooks:
  * `.st-key-<key>`     – class Streamlit adds to every widget created with key=...
  * `[data-testid=...]` – Streamlit test IDs (stMetric, stAlert, stTab, stException, ...)
  * custom classes from app.py (.kpi, .step, .mail-meta, .mail-body, .health)
Inactive tabs stay in the DOM, so lookups only consider displayed elements.
"""
from __future__ import annotations

import re
import sys
import time

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from common.test_data import LLM_TIMEOUT, UI_TIMEOUT


class DashboardPage:
    def __init__(self, driver: WebDriver, base_url: str):
        self.driver = driver
        self.base_url = base_url

    # ------------------------------------------------------------ helpers
    def _wait(self, timeout: float = UI_TIMEOUT) -> WebDriverWait:
        return WebDriverWait(self.driver, timeout, ignored_exceptions=[StaleElementReferenceException])

    def _css(self, selector: str, root=None) -> list[WebElement]:
        return (root or self.driver).find_elements(By.CSS_SELECTOR, selector)

    def _visible(self, selector: str) -> list[WebElement]:
        return [e for e in self._css(selector) if e.is_displayed()]

    def _click(self, selector: str, timeout: float = UI_TIMEOUT) -> None:
        self._wait(timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector))).click()
        self.wait_idle()

    @staticmethod
    def _type(el: WebElement, value: str) -> None:
        """Replace a field's value. el.clear() does not reset React-controlled Streamlit inputs."""
        el.send_keys(Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        el.send_keys(value)

    @staticmethod
    def _text(el: WebElement) -> str:
        return (el.get_attribute("textContent") or "").strip()

    def wait_idle(self, timeout: float = UI_TIMEOUT) -> None:
        """Wait for the Streamlit rerun to finish (no 'Running…' widget, no stale elements)."""
        time.sleep(0.4)  # let the rerun start
        self._wait(timeout).until(lambda d: not self._css('[data-testid="stStatusWidget"]')
                                  and not self._css('[data-stale="true"]'))

    # ------------------------------------------------------------ page
    def open(self) -> "DashboardPage":
        self.driver.get(self.base_url)
        self._wait(60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".app-header")))
        self._wait().until(lambda d: self._css('[class*="st-key-open_"]'))
        self.wait_idle()
        return self

    def header_text(self) -> str:
        return self._text(self._css(".app-header")[0])

    def has_exception(self) -> bool:
        return bool(self._css('[data-testid="stException"]'))

    def kpi(self, label: str) -> str:
        for card in self._css(".kpi"):
            if self._text(card.find_element(By.CSS_SELECTOR, ".label")).lower() == label.lower():
                return self._text(card.find_element(By.CSS_SELECTOR, ".value"))
        raise AssertionError(f"KPI '{label}' not found")

    def health(self) -> dict[str, bool]:
        return {self._text(h)[2:].strip(): self._text(h).startswith("🟢") for h in self._css(".health")}

    def tab_names(self) -> list[str]:
        return [self._text(t) for t in self._visible('[data-testid="stTab"]')]

    def open_tab(self, name: str) -> None:
        for tab in self._visible('[data-testid="stTab"]'):
            if name in self._text(tab):
                tab.click()
                time.sleep(0.3)
                return
        raise AssertionError(f"Tab '{name}' not found")

    # ------------------------------------------------------------ inbox
    def inbox_ids(self) -> list[int]:
        ids = []
        for el in self._css('[class*="st-key-open_"]'):
            key = next(c for c in el.get_attribute("class").split() if c.startswith("st-key-open_"))
            ids.append(int(key.rsplit("_", 1)[1]))
        return ids

    def inbox_count(self) -> int:
        title = next(self._text(t) for t in self._css(".section-title") if "Customer emails" in self._text(t))
        return int(re.search(r"\((\d+)\)", title).group(1))

    def open_email(self, email_id: int) -> None:
        self._click(f".st-key-open_{email_id} button")
        self._wait().until(lambda d: f"#{email_id}" in self.email_header())

    def open_button_label(self, email_id: int) -> str:
        return self._text(self._css(f".st-key-open_{email_id} button")[0])

    def email_header(self) -> str:
        return next((self._text(m) for m in self._css(".mail-meta") if self._text(m).startswith("From")), "")

    def email_body(self) -> str:
        return self._text(self._css(".mail-body")[0])

    def _choose(self, key: str, label: str) -> None:
        """Pick an option in a Streamlit selectbox (react-aria combobox)."""
        self._wait().until(EC.element_to_be_clickable((By.CSS_SELECTOR, f".st-key-{key} input"))).click()
        self._wait().until(EC.element_to_be_clickable(
            (By.XPATH, f"//*[@role='option'][normalize-space()='{label}']"))).click()

    def set_filter(self, label: str) -> None:
        self._choose("status_filter", label)
        self.wait_idle()

    def simulate_email(self, name: str, email: str, subject: str, body: str, priority: str = "NORMAL") -> None:
        for exp in self._css('[data-testid="stExpander"]'):
            if "Simulate incoming email" in self._text(exp):
                exp.find_element(By.CSS_SELECTOR, "summary").click()
                break
        self._wait().until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".st-key-sim_name input")))
        for key, value in (("sim_name", name), ("sim_email", email), ("sim_subject", subject)):
            self._type(self._css(f".st-key-{key} input")[0], value)
        self._type(self._css(".st-key-sim_body textarea")[0], body)
        self._choose("sim_priority", priority)
        self._click(".st-key-sim_submit button")

    # ------------------------------------------------------------ AI processing
    def process_button_visible(self) -> bool:
        return bool(self._visible(".st-key-process_email button"))

    def process_email(self, timeout: float = LLM_TIMEOUT) -> None:
        self._css(".st-key-process_email button")[0].click()
        self._wait(timeout).until(lambda d: "Intent" in self.metrics() or self.has_exception())
        self.wait_idle()

    def metrics(self) -> dict[str, str]:
        out = {}
        for m in self._visible('[data-testid="stMetric"]'):
            label = self._text(m.find_element(By.CSS_SELECTOR, '[data-testid="stMetricLabel"]'))
            out[label] = self._text(m.find_element(By.CSS_SELECTOR, '[data-testid="stMetricValue"]'))
        return out

    def metric(self, label: str) -> str:
        return self.metrics()[label]

    def pipeline_steps(self) -> dict[str, str]:
        """{'Intent Identification': 'done' | 'fail' | 'skip', ...}"""
        steps = {}
        for el in self._css(".pipeline .step"):
            state = next(c for c in el.get_attribute("class").split() if c in ("done", "fail", "skip"))
            name = re.sub(r"^\W+|\s*[✓✕–].*$", "", self._text(el)).strip()
            steps[name] = state
        return steps

    def visible_text(self) -> str:
        return self._text(self._css('[data-testid="stMain"]')[0])

    # ------------------------------------------------------------ draft + RM actions
    def draft_subject(self) -> str:
        return self._visible('[class*="st-key-subj_"] input')[0].get_attribute("value")

    def draft_body(self) -> str:
        areas = self._visible('[class*="st-key-body_"] textarea') or self._visible('[class*="st-key-fb_"] textarea')
        return areas[0].get_attribute("value")

    def edit_body(self, text_to_append: str) -> None:
        area = self._visible('[class*="st-key-body_"] textarea')[0]
        area.click()
        self.driver.execute_script("arguments[0].setSelectionRange(arguments[0].value.length, arguments[0].value.length)", area)
        area.send_keys(text_to_append)
        self._css(".app-header")[0].click()   # blur -> Streamlit commits the value
        self.wait_idle()

    def button_enabled(self, action: str) -> bool:
        """action: accept | edit | reject"""
        prefix = {"accept": "acc", "edit": "edit", "reject": "rej"}[action]
        return self._visible(f'[class*="st-key-{prefix}_"] button')[0].is_enabled()

    def accept(self) -> None:
        self._click('[class*="st-key-acc_"] button')

    def accept_with_edits(self) -> None:
        self._click('[class*="st-key-edit_"] button')

    def reject(self, comment: str = "") -> None:
        if comment:
            self._type(self._visible('[class*="st-key-cm_"] input')[0], comment)
            self._css(".app-header")[0].click()
            self.wait_idle()
        self._click('[class*="st-key-rej_"] button')

    def reprocess_button_visible(self) -> bool:
        return bool(self._visible('[class*="st-key-re_"] button'))

    def alert_texts(self) -> list[str]:
        return [self._text(a) for a in self._visible('[data-testid="stAlert"]')]

    def expander_titles(self) -> list[str]:
        return [self._text(e.find_element(By.CSS_SELECTOR, "summary [data-testid='stMarkdownContainer']"))
                for e in self._visible('[data-testid="stExpander"]')]

    def trace_id(self) -> str | None:
        self.open_tab("Agent trace")
        match = re.search(r"Trace ID:\s*([0-9a-f]{32})", self.visible_text())
        return match.group(1) if match else None
