# UI test automation: ABC Bank RM Assistant

This folder contains browser tests for the Streamlit app, implemented twice so you can compare the tools:

| Folder | Tool | Driver |
|---|---|---|
| `selenium_tests/` | Selenium WebDriver 4 | Google Chrome (Selenium Manager downloads chromedriver automatically) |
| `playwright_tests/` | Playwright for Python | Bundled Chromium (`playwright install chromium`) |

Both suites cover the same scenarios with the same test code. Only the page objects in `*/pages/dashboard.py` differ, so the two tools can be compared side by side.

> The folders are named `selenium_tests` and `playwright_tests`, not `selenium` and `playwright`. Folders with the bare names would shadow the real Python packages on `sys.path`.

## How to approach testing this app

The app has three layers that fail in different ways, so each is tested differently.

| Layer | What can go wrong | How it's tested | Marker | LLM? | Speed |
|---|---|---|---|---|---|
| UI shell | Page doesn't load, KPIs wrong, inbox or filter broken | `test_smoke.py`, `test_inbox.py` | `smoke` | No | Seconds |
| RM workflow | Accept, Accept with edits or Reject saves the wrong thing | `test_rm_actions.py`. The AI draft is seeded straight into the DB (`common/test_db.seed_draft`), so these tests are deterministic. | `actions` | No | Seconds |
| Agents + LLM | Wrong routing, authentication bypass, wrong figures, missing traces | `test_agent_flows.py`: the real LangGraph pipeline on local llama3.1 | `llm` | Yes | 20–90 s per email |

Principles:
- **Isolation.** The tests start their own app on port **8503**, backed by the database **`abc_bank_rm_test`** and the Phoenix project **`abc-bank-rm-tests`**. The demo on 8502 and its data are never touched; `common/test_db.py` refuses to reset `abc_bank_rm`.
- **Independent tests.** The database is reset before every test (`fresh_db`, about 1 s), and every test opens a fresh browser session. Tests can run in any order and any subset.
- **Deterministic where possible.** The LLM is used only in the `llm` tests. Everything else seeds data directly.
- **LLM output varies between runs.** The `llm` tests assert facts and structure, never wording. Examples:
  - the balance figure appears in the draft
  - the full account number never does
  - an unverified sender gets no amounts
  - the tool spans exist in Phoenix
- **Stable selectors.** Tests locate elements by:
  - the `st-key-<key>` class Streamlit adds to widgets that have a `key`
  - Streamlit `data-testid`s (`stMetric`, `stAlert`, `stTab`, …)
  - the app's own classes (`.kpi`, `.step`, `.mail-meta`)

  They never rely on generated CSS class names.
- **Wait for reruns.** Streamlit reruns the script after every interaction. The page objects' `wait_idle()` waits until the "Running…" widget and any `data-stale="true"` elements are gone. Text boxes are committed by blurring them.

## Setup (one time)
```bash
cd abc-bank-rm-demo
source .venv/bin/activate
pip install -r ui_automation/requirements.txt
playwright install chromium
```
You also need:
- **Google Chrome**, for Selenium
- **Docker** running the `postgres` container (and `ollama` plus `phoenix` for the `llm` tests)

## Running the tests
Run from the `ui_automation/` folder. The suites share port 8503, so **run them one after the other, not in parallel**.

```bash
cd ui_automation

# fast suites, no LLM (~30 s each)
pytest selenium_tests   -m "not llm"
pytest playwright_tests -m "not llm"

# only one layer
pytest selenium_tests -m smoke
pytest playwright_tests -m actions

# end-to-end through the real LLM (~4–6 min per suite)
pytest selenium_tests   -m llm
pytest playwright_tests -m llm

# watch the browser
pytest playwright_tests -m smoke --headed --slowmo 300
pytest selenium_tests   -m smoke --headed          # --headed is shared by both suites

# a single test
pytest "playwright_tests/tests/test_rm_actions.py::test_accept_with_edits" --headed
```
If Ollama isn't reachable, the `llm` tests are skipped automatically.

## Reports and debugging
```bash
# HTML report (either suite)
pytest selenium_tests -m "not llm" --html=reports/selenium.html --self-contained-html

# Playwright: keep a full trace, screenshot and video of each failing test
pytest playwright_tests --tracing=retain-on-failure --screenshot=only-on-failure --video=retain-on-failure --output=reports/playwright
playwright show-trace reports/playwright/<test-folder>/trace.zip     # step-through DOM snapshots, network and console
```
Other output:
- **Selenium** saves a screenshot of every failing test to `reports/selenium/<test>.png`.
- **The test app's server log** is at `reports/test_app_server.log`.
- **Phoenix traces from test runs** are in the `abc-bank-rm-tests` project at http://localhost:6006.

## Useful environment variables
| Variable | Default | Purpose |
|---|---|---|
| `UI_TEST_PORT` | `8503` | Port for the test app instance |
| `UI_TEST_PG_DB` | `abc_bank_rm_test` | Test database (created automatically) |
| `UI_TEST_PHOENIX_PROJECT` | `abc-bank-rm-tests` | Phoenix project that receives the test traces |
| `UI_BASE_URL` | – | Test an already running instance instead of starting one. It must use the test DB. |

## Layout
```
ui_automation/
├── conftest.py            test env (DB, Phoenix project), app_url / base_url, fresh_db, auto-skip of llm tests
├── pytest.ini             markers: smoke, actions, llm
├── common/                app_server.py (starts app on 8503), test_db.py (reset/seed/read), test_data.py, phoenix.py
├── selenium_tests/        conftest.py (Chrome driver, failure screenshots), pages/dashboard.py, tests/
├── playwright_tests/      conftest.py (viewport), pages/dashboard.py, tests/
└── reports/               generated: HTML reports, screenshots, traces, server log
```

## Selenium vs Playwright in this project
| | Selenium | Playwright |
|---|---|---|
| Waiting | Explicit `WebDriverWait` everywhere | Auto-waiting locators and `expect()` |
| Hidden tab content | Filter with `is_displayed()` | `:visible` in the selector |
| Typing into React inputs | `clear()` doesn't reset them; use select-all + type | `fill()` just works |
| Debugging | Screenshots | Trace viewer (DOM snapshots per step), video, `--slowmo`, codegen |
| Browsers | Real installed Chrome, Firefox, Safari (and Grid for remote runs) | Bundled Chromium, Firefox and WebKit |

## Adding a test
1. Add any new interaction to **both** `pages/dashboard.py` files, keeping the method names identical.
2. Write the test once in `selenium_tests/tests/`, and copy it to `playwright_tests/tests/`.
3. For stable selectors, give new Streamlit widgets a `key=` in `app.py`.
4. Choose a marker: `smoke` and `actions` tests must not call the LLM. Seed data with `common/test_db.py` instead.

## Known issue these tests catch
`test_account_query_authenticates_and_uses_core_banking` checks that Rahul's draft states **Rs 18,45,230.55**. Llama 3.1 sometimes rewrites Indian-format numbers wrongly (for example "Rs 1,84,523.55"). When that happens the test fails. That is a real accuracy bug in the drafting agent, not a flaky test.
