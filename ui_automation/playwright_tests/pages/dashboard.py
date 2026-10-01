"""Page Object for the RM Assistant dashboard – Playwright implementation.

Same API as selenium_tests/pages/dashboard.py so the two suites read identically.
Playwright auto-waits for elements to be actionable; `:visible` skips content in inactive tabs.
"""
from __future__ import annotations

import re
import time

from playwright.sync_api import Page, expect

from common.test_data import LLM_TIMEOUT, UI_TIMEOUT

MS = 1000


class DashboardPage:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url
        page.set_default_timeout(UI_TIMEOUT * MS)

    # ------------------------------------------------------------ helpers
    def wait_idle(self, timeout: float = UI_TIMEOUT) -> None:
        """Wait for the Streamlit rerun to finish (no 'Running…' widget, no stale elements)."""
        time.sleep(0.4)  # let the rerun start
        expect(self.page.locator('[data-testid="stStatusWidget"]')).to_have_count(0, timeout=timeout * MS)
        expect(self.page.locator('[data-stale="true"]')).to_have_count(0, timeout=timeout * MS)

    def _click(self, selector: str) -> None:
        self.page.locator(selector).locator("visible=true").first.click()
        self.wait_idle()

    def _choose(self, key: str, label: str) -> None:
        """Pick an option in a Streamlit selectbox (react-aria combobox)."""
        field = self.page.locator(f".st-key-{key} input")
        # the sidebar scrolls separately and a click can land while it's still settling, leaving the
        # listbox closed – retry until aria-expanded flips
        field.scroll_into_view_if_needed()
        for _ in range(4):
            time.sleep(0.3)
            field.click()
            if field.get_attribute("aria-expanded") == "true":
                break
        self.page.get_by_role("option", name=label, exact=True).click()

    def _blur(self) -> None:
        self.page.locator(".app-header").click()   # Streamlit commits text widgets on blur
        self.wait_idle()

    @staticmethod
    def _clean(text: str | None) -> str:
        return (text or "").strip()

    # ------------------------------------------------------------ page
    def open(self) -> "DashboardPage":
        self.page.goto(self.base_url)
        expect(self.page.locator(".app-header")).to_be_visible(timeout=60 * MS)
        expect(self.page.locator('[class*="st-key-open_"]').first).to_be_attached()
        self.wait_idle()
        return self

    def header_text(self) -> str:
        return self._clean(self.page.locator(".app-header").text_content())

    def has_exception(self) -> bool:
        return self.page.locator('[data-testid="stException"]').count() > 0

    def kpi(self, label: str) -> str:
        card = self.page.locator(".kpi").filter(
            has=self.page.locator(".label", has_text=re.compile(f"^{re.escape(label)}$", re.I)))
        return self._clean(card.locator(".value").text_content())

    def health(self) -> dict[str, bool]:
        return {t.strip()[2:].strip(): t.strip().startswith("🟢")
                for t in self.page.locator(".health").all_text_contents()}

    def tab_names(self) -> list[str]:
        return [t.strip() for t in self.page.locator('[data-testid="stTab"]:visible').all_text_contents()]

    def open_tab(self, name: str) -> None:
        self.page.locator('[data-testid="stTab"]:visible', has_text=name).first.click()
        time.sleep(0.3)

    # ------------------------------------------------------------ inbox
    def inbox_ids(self) -> list[int]:
        classes = self.page.locator('[class*="st-key-open_"]').evaluate_all(
            "els => els.map(e => [...e.classList].find(c => c.startsWith('st-key-open_')))")
        return [int(c.rsplit("_", 1)[1]) for c in classes]

    def inbox_count(self) -> int:
        title = self.page.locator(".section-title", has_text="Customer emails").text_content()
        return int(re.search(r"\((\d+)\)", title).group(1))

    def open_email(self, email_id: int) -> None:
        self._click(f".st-key-open_{email_id} button")
        expect(self.page.locator(".mail-meta", has_text="From")).to_contain_text(f"#{email_id}")

    def open_button_label(self, email_id: int) -> str:
        return self._clean(self.page.locator(f".st-key-open_{email_id} button").text_content())

    def email_header(self) -> str:
        loc = self.page.locator(".mail-meta", has_text="From")
        return self._clean(loc.first.text_content()) if loc.count() else ""

    def email_body(self) -> str:
        return self._clean(self.page.locator(".mail-body").text_content())

    def set_filter(self, label: str) -> None:
        self._choose("status_filter", label)
        self.wait_idle()

    def simulate_email(self, name: str, email: str, subject: str, body: str, priority: str = "NORMAL") -> None:
        self.page.locator('[data-testid="stExpander"] summary', has_text="Simulate incoming email").click()
        self.page.locator(".st-key-sim_name input").fill(name)
        self.page.locator(".st-key-sim_email input").fill(email)
        self.page.locator(".st-key-sim_subject input").fill(subject)
        self.page.locator(".st-key-sim_body textarea").fill(body)
        self._choose("sim_priority", priority)
        self._click(".st-key-sim_submit button")

    # ------------------------------------------------------------ AI processing
    def process_button_visible(self) -> bool:
        return self.page.locator(".st-key-process_email button").is_visible()

    def process_email(self, timeout: float = LLM_TIMEOUT) -> None:
        self.page.locator(".st-key-process_email button").click()
        done = self.page.locator('[data-testid="stMetricLabel"]:visible', has_text="Intent").or_(
            self.page.locator('[data-testid="stException"]'))
        expect(done.first).to_be_visible(timeout=timeout * MS)
        self.wait_idle()

    def metrics(self) -> dict[str, str]:
        out = {}
        for m in self.page.locator('[data-testid="stMetric"]:visible').all():
            label = self._clean(m.locator('[data-testid="stMetricLabel"]').text_content())
            out[label] = self._clean(m.locator('[data-testid="stMetricValue"]').text_content())
        return out

    def metric(self, label: str) -> str:
        return self.metrics()[label]

    def pipeline_steps(self) -> dict[str, str]:
        """{'Intent Identification': 'done' | 'fail' | 'skip', ...}"""
        steps = {}
        for el in self.page.locator(".pipeline .step").all():
            state = next(c for c in el.get_attribute("class").split() if c in ("done", "fail", "skip"))
            name = re.sub(r"^\W+|\s*[✓✕–].*$", "", self._clean(el.text_content())).strip()
            steps[name] = state
        return steps

    def visible_text(self) -> str:
        return self.page.locator('[data-testid="stMain"]').inner_text()

    # ------------------------------------------------------------ draft + RM actions
    def draft_subject(self) -> str:
        return self.page.locator('[class*="st-key-subj_"] input:visible').input_value()

    def draft_body(self) -> str:
        editable = self.page.locator('[class*="st-key-body_"] textarea:visible')
        area = editable if editable.count() else self.page.locator('[class*="st-key-fb_"] textarea:visible')
        return area.input_value()

    def edit_body(self, text_to_append: str) -> None:
        area = self.page.locator('[class*="st-key-body_"] textarea:visible')
        area.fill(area.input_value() + text_to_append)
        self._blur()

    def button_enabled(self, action: str) -> bool:
        """action: accept | edit | reject"""
        prefix = {"accept": "acc", "edit": "edit", "reject": "rej"}[action]
        return self.page.locator(f'[class*="st-key-{prefix}_"] button:visible').is_enabled()

    def accept(self) -> None:
        self._click('[class*="st-key-acc_"] button')

    def accept_with_edits(self) -> None:
        self._click('[class*="st-key-edit_"] button')

    def reject(self, comment: str = "") -> None:
        if comment:
            self.page.locator('[class*="st-key-cm_"] input:visible').fill(comment)
            self._blur()
        self._click('[class*="st-key-rej_"] button')

    def reprocess_button_visible(self) -> bool:
        return self.page.locator('[class*="st-key-re_"] button:visible').count() > 0

    def alert_texts(self) -> list[str]:
        return [t.strip() for t in self.page.locator('[data-testid="stAlert"]:visible').all_text_contents()]

    def expander_titles(self) -> list[str]:
        return [t.strip() for t in self.page.locator(
            '[data-testid="stExpander"]:visible summary [data-testid="stMarkdownContainer"]').all_text_contents()]

    def trace_id(self) -> str | None:
        self.open_tab("Agent trace")
        match = re.search(r"Trace ID:\s*([0-9a-f]{32})", self.visible_text())
        return match.group(1) if match else None
