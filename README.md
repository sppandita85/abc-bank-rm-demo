# ABC Bank – RM Assistant (Agentic AI)

An agentic assistant for Relationship Managers. It classifies incoming customer emails and authenticates the customer when the query is account-related. It then fetches data from the product catalogue or core banking and drafts a reply. The RM **accepts, rejects or edits** the draft. Every step is traced in **Arize Phoenix**.

```
email ─► intent_identification_agent ─┬─ non_account ─► product_information_agent ─┐
                                      └─ account ─► authentication_agent           │
                                                     ├─ SUCCESS ─► core_banking_agent ─┤
                                                     └─ NOT_FOUND ─────────────────────┤
                                                                   email_drafting_agent ◄┘ ─► RM review
```

| Agent | What it does |
|---|---|
| `intent_identification_agent` | Llama 3.1 (JSON mode) classifies the email as `account` or `non_account`, with a sub-intent (balance, transactions, dispute, loan, card, fixed_deposit, account_summary, product_info) and a product category. Falls back to keyword matching if the LLM fails. |
| `authentication_agent` | Pass-through for now. It maps the sender to a registered customer email. `verify()` is the hook for real authentication (OTP, KBA, …). |
| `product_information_agent` | Ranks products in the Postgres `products` table by category and keyword relevance. |
| `core_banking_agent` | Runs fixed, parameterised queries on `accounts`, `transactions`, `loans`, `cards` and `fixed_deposits`, chosen by sub-intent. It also detects duplicate debits for disputes. The LLM never writes SQL. |
| `email_drafting_agent` | Writes the reply using only the retrieved facts. It masks account numbers, makes no promises, and adds internal notes for the RM. |

## Stack (all local)
- **Postgres**: existing docker container `postgres` on `localhost:5433`, database `abc_bank_rm`
- **Ollama**: existing container on `localhost:11434`, model `llama3.1:latest` (8B)
- **Arize Phoenix**: existing container `phoenix`, UI at http://localhost:6006, project `abc-bank-rm`
- LangGraph, LangChain-Ollama, OpenInference instrumentation, Streamlit

## Setup & run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # adjust if your ports differ

python -m db.init_db               # creates abc_bank_rm and loads schema + seed data (re-run to reset the demo)
streamlit run app.py               # http://localhost:8502
```

CLI run for a single email (prints each agent step, the draft and the trace id):
```bash
python -m graph.workflow 3
```

## Using the app
1. The inbox (left) shows each email with its status, intent and priority badges. Use **Simulate incoming email** in the sidebar to add new ones.
2. Open an email and click **Process with AI agents** to watch each agent complete live.
3. Review the result:
   - the pipeline view, with skipped branches struck through
   - the classification metrics
   - the draft, the retrieved data, and the per-agent trace
4. Choose an action:
   - **Accept**: sends the draft as-is.
   - **Accept with edits**: enabled once you change the subject or body. The original draft is kept for audit.
   - **Reject**: needs a comment. You can re-process the email afterwards.
5. **Open this trace in Arize Phoenix** opens the full span tree: `rm_email_pipeline` → `LangGraph` → each AGENT → its `ChatOllama` LLM span (prompt, response, token counts) and its database TOOL spans (tool description, parameter JSON schema, input, SQL in `db.statement`, rows returned).

## Seeded demo data
- 10 customers, e.g. `rahul.mehta@example.com` (Premier, home loan, FD, card) and `ananya.iyer@example.com` (duplicate Croma UPI debit)
- 11 accounts, about 170 transactions, 5 loans, 5 cards, 5 FDs, 20 products
- 15 inbox emails: 8 account queries and 7 product queries. Send from an unregistered address to see the failed-authentication path.

## Project layout
```
config.py                 settings (.env)
db/                       schema.sql, seed.sql, init_db.py, connection.py, repository.py
agents/                   state, llm helpers, database tools (tools.py) and the five agents
graph/workflow.py         LangGraph wiring + process_email()
observability/tracing.py  Phoenix registration and LangChain/LangGraph instrumentation
app.py                    Streamlit UI
ui_automation/            Selenium + Playwright UI test suites (see ui_automation/README.md)
tests/ui_test_cases.md    manual / Cowork test script
```

## Testing
Automated browser tests (Selenium and Playwright) live in [ui_automation/](ui_automation/README.md). They start their own app instance on port 8503 with a separate test database, so the demo is never affected:
```bash
cd ui_automation && pytest selenium_tests -m "not llm" && pytest playwright_tests -m "not llm"
```
