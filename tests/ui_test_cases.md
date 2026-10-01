# ABC Bank RM Assistant: UI test cases

**App under test:** http://localhost:8502
**Phoenix (observability):** http://localhost:6006

## Instructions for the tester (Claude in Cowork)
You are testing a Streamlit web app in the browser. Run the test cases **in order**. Later cases depend on the state that earlier ones leave behind.

For each case:
1. Follow the steps exactly.
2. Check every item under **Expected**.
3. Record **PASS**, **FAIL** or **BLOCKED** in the results table at the end, with a one-line note. For any FAIL, take a screenshot and quote the text you saw.

Things to know about this app:
- **AI steps are slow.** The Process with AI agents and Re-process buttons run a local LLM and take **20–90 seconds**. Wait up to **150 seconds** for the progress panel to turn into "Draft ready in …s" before judging the result. Don't click again while it's running.
- **Draft wording varies between runs.** Check the facts, figures and structure listed under Expected, not exact sentences.
- **Text edits need committing.** After typing in a Streamlit text box, click somewhere outside it or press **Cmd+Enter** so the app registers the change. Buttons that depend on the edit update only after that.
- **The page reruns after most clicks.** Wait until the "Running…" indicator in the top-right corner disappears before your next action.
- **Opening an email.** In the left-hand inbox list, each email card has an **Open** button. The selected card's button reads **Viewing**. Identify emails by sender name and subject.

## Precondition: reset the demo data
Before the first run, the human operator runs this in the project folder:
```bash
source .venv/bin/activate && python -m db.init_db
```
After that, reload http://localhost:8502. The inbox should hold 15 emails, all with status **New**.

---

## UI-01: Dashboard loads
**Steps**
1. Open http://localhost:8502 and wait for the page to finish loading.

**Expected**
- A dark blue header reads **"🏦 ABC Bank · RM Assistant"** with today's date on the right.
- There are five KPI cards: **New queries = 15**, **Pending review = 0**, **Approved = 0**, **Rejected = 0**, and **Avg. turnaround**.
- There are two tabs: **📥 Inbox** and **📊 Activity history**.
- The left sidebar shows the RM card **Priya Sharma, Senior Relationship Manager**.
- Under **System health**, three green dots (🟢) appear for **PostgreSQL**, **Ollama · llama3.1:latest** and **Arize Phoenix**.
- There's no red error box or Python traceback anywhere on the page.

## UI-02: Inbox list and email detail
**Steps**
1. On the Inbox tab, look at the left-hand list.
2. Click **Open** on the card from **Amit Verma** with subject **"Home loan interest rates"**.

**Expected**
- The list heading reads **"Customer emails (15)"**. The newest email, from **Rohan Desai**, is at the top.
- Each card shows the sender, the time, the subject, a **New** status badge and a priority badge (some are **High**).
- The right panel shows **From Amit Verma <prospect.amit@gmail.com>**, the subject, and the full body mentioning a flat in Pune worth Rs 90 lakh.
- A blue info message says the query hasn't been processed yet.
- A **🤖 Process with AI agents** button is visible.
- Amit's card button now reads **Viewing**.

## UI-03: Inbox status filter
**Steps**
1. In the sidebar under **Inbox filter**, choose **Approved**.
2. Set the filter back to **All**.

**Expected**
- With **Approved** selected, the list heading reads **"Customer emails (0)"** and no cards appear.
- With **All** selected, the list returns to 15 emails.

## UI-04: Non-account query goes to the product information agent
**Steps**
1. Open **Amit Verma, "Home loan interest rates"**.
2. Click **🤖 Process with AI agents** and wait until it finishes.

**Expected**
- While it runs, a progress panel titled **"Running AI agents…"** lists each agent as it completes.
- When it finishes, the panel collapses to **"Draft ready in Xs"**.
- The pipeline row shows green chips for **🧠 Intent Identification ✓ → 📚 Product Information ✓ → ✍️ Email Drafting ✓**. There are no Authentication or Core Banking chips.
- The metrics read **Intent = Non-Account**, **Sub-intent = Product Info** and **Authentication = N/A**.
- **✉️ Draft reply** tab:
  - The subject is pre-filled.
  - The body starts with **"Dear Amit"**, mentions home loan interest rates such as **8.35%**, and ends with **"Warm regards, Priya Sharma, Senior Relationship Manager, ABC Bank"**.
  - A yellow **"🔒 Internal notes for RM"** box is shown.
- **🗄️ Retrieved data** tab: the caption reads **"Source: Product Information Database (PostgreSQL)"**, and a **Products** table includes **ABC Home Loan**.
- Amit's inbox card shows a **Pending review** badge and a **Non-account** badge.
- The **Pending review** KPI is 1 and **New queries** is 14.

## UI-05: Account query goes through authentication and core banking
**Steps**
1. Open **Rahul Mehta, "Current balance in my savings account"**. It's the oldest email, at the bottom of the list.
2. Click **🤖 Process with AI agents** and wait.

**Expected**
- The pipeline row shows **🧠 Intent Identification ✓ → 🔐 Authentication ✓ → 🏦 Core Banking ✓ → ✍️ Email Drafting ✓**.
- The metrics read **Intent = Account**, **Sub-intent = Balance** and **Authentication = SUCCESS**.
- The draft body states a balance of **Rs 18,45,230.55**. Small formatting differences, such as a missing comma, are acceptable.
- The draft shows the account number masked, for example **XXXXXXXXXX0001**. The full number **50100012340001** must **not** appear in the draft.
- **Retrieved data** tab: the caption reads **"Source: Core Banking System (PostgreSQL)"** with **Customer ID C1001**. An **Accounts** table lists two accounts (SAVINGS and CURRENT).

## UI-06: Duplicate-debit dispute
**Steps**
1. Open **Ananya Iyer, "Amount debited twice - Croma purchase"**.
2. Click **🤖 Process with AI agents** and wait.

**Expected**
- The metrics read **Intent = Account** and **Sub-intent = Dispute**.
- The **Retrieved data** tab has a **Suspected Duplicate Debits** table with one row: **UPI - Croma Electronics**, amount **18999**, and two reference numbers.
- A **Recent Transactions** table is also shown.
- The draft acknowledges the duplicate debit of **Rs 18,999**. It must **not** promise a refund date or timeframe such as "within 24–48 hours".
- The internal notes suggest raising a dispute or ticket, or something similar.

## UI-07: Accept the draft as-is
**Steps**
1. Open **Amit Verma, "Home loan interest rates"**, which was processed in UI-04.
2. Without editing anything, click **✅ Accept**.

**Expected**
- A green banner reads **"Accepted by Priya Sharma on <date, time>"**.
- The Subject and Email body fields are greyed out and can't be edited.
- The Accept, Accept with edits and Reject buttons are gone, and a **🔄 Re-process with AI** button is shown.
- Amit's inbox card shows an **Approved** badge.
- The **Approved** KPI is 1 and **Pending review** is 2.

## UI-08: Accept with edits
**Steps**
1. Open **Rahul Mehta, "Current balance in my savings account"**, which was processed in UI-05.
2. Before editing, confirm that **✏️ Accept with edits** is disabled and **✅ Accept** is enabled.
3. Click at the end of the **Email body (editable)** text box. Add a new line:
   `P.S. I will call you this afternoon regarding the payment.`
   Then commit the edit (click outside the box or press Cmd+Enter).
4. Click **✏️ Accept with edits**.

**Expected**
- After step 3:
  - a caption appears: **"✏️ You have edited the draft — use Accept with edits to send your version."**
  - **✅ Accept** is disabled
  - **✏️ Accept with edits** is enabled
- After step 4, a green banner reads **"Accepted With Edits by Priya Sharma on …"**.
- The read-only body includes the P.S. line you added.
- A **"View original AI draft"** expander appears. When you open it, it shows the draft *without* the P.S. line.
- The **Approved** KPI is 2, and its hint reads **"1 with edits"**.

## UI-09: Reject needs a comment
**Steps**
1. Open **Ananya Iyer, "Amount debited twice - Croma purchase"**, which was processed in UI-06.
2. Leave **Comment (required to reject)** empty and click **❌ Reject**.
3. Type `Please include the transaction reference numbers` in the comment box, commit it, then click **❌ Reject**.

**Expected**
- After step 2, a yellow warning reads **"Please add a comment explaining the rejection."** and the email stays in **Pending review**.
- After step 3, a red banner reads **"Rejected by Priya Sharma on … — Please include the transaction reference numbers"**.
- Ananya's card shows a **Rejected** badge, and a **🔄 Re-process with AI** button is shown.
- The **Rejected** KPI is 1.

## UI-10: Re-process a rejected email
**Steps**
1. With Ananya's email still open, click **🔄 Re-process with AI** and wait.

**Expected**
- The progress panel runs again and ends with **"Draft ready in Xs"**.
- A fresh, editable draft appears with the Accept, Accept with edits and Reject buttons.
- Ananya's card badge changes back to **Pending review**.

## UI-11: Unregistered sender fails authentication
**Steps**
1. In the sidebar, expand **✉️ Simulate incoming email** and fill in:
   - Sender name: `Suresh Pillai`
   - Sender email: `unknown.person@gmail.com`
   - Subject: `My account balance`
   - Body: `Hi, please tell me the balance in my savings account. Thanks, Suresh`
   - Priority: `HIGH`
2. Click **Send to RM inbox**.
3. The new email opens automatically; if it doesn't, open it. Click **🤖 Process with AI agents** and wait.

**Expected**
- A toast says **"New email #16 received"**. The email appears at the top of the inbox as **New** with a **High** priority badge. The **New queries** KPI goes up by 1.
- After processing:
  - The pipeline shows **🔐 Authentication ✕** as a red chip, and **🏦 Core Banking** is struck through as skipped.
  - The metrics read **Intent = Account** and **Authentication = NOT_FOUND**.
  - The draft politely asks the sender to write from their registered email address or to contact the branch to verify their identity.
  - The draft contains **no** balance, account number or other account data.
  - The **Retrieved data** tab shows "No data retrieved" or "No data was retrieved for this query."

## UI-12: Registered customer asks about a credit card
**Steps**
1. Expand **✉️ Simulate incoming email** again. Keep the default values: sender **Rahul Mehta, rahul.mehta@example.com**, subject **"Credit card outstanding"**. Click **Send to RM inbox**.
2. Open the new email if it isn't already open, click **🤖 Process with AI agents** and wait.

**Expected**
- The metrics read **Intent = Account**, **Sub-intent = Card** and **Authentication = SUCCESS**.
- The **Retrieved data** tab has a **Cards** table with **4532-XXXX-XXXX-1001, ABC Infinite Credit Card**.
- The draft states the outstanding amount (**Rs 1,87,550**) and a due date.

## UI-13: Agent trace and Phoenix deep link
**Steps**
1. On any processed email (for example, Rahul's credit card email from UI-12), open the **🧭 Agent trace** tab.
2. Expand the **🧠 Intent Identification** row.
3. Click **🔭 Open this trace in Arize Phoenix**.

**Expected**
- The tab shows a **Trace ID** of 32 hex characters.
- There's one expandable row per agent that ran, each with a summary and a duration in ms.
- Expanding a row shows JSON output. The intent row includes `intent`, `sub_intent` and `method: "llm"`.
- Phoenix opens at localhost:6006, in project **abc-bank-rm**, showing that trace.
- The trace tree contains:
  - **rm_email_pipeline**, with **LangGraph** under it
  - under LangGraph, AGENT spans: **intent_identification_agent**, **authentication_agent**, **core_banking_agent** and **email_drafting_agent**
  - **ChatOllama** LLM spans under the intent and drafting agents
  - a TOOL span named **get_cards** under core_banking_agent, and **lookup_customer_by_email** under authentication_agent
- Clicking the **get_cards** span shows the tool's description, its parameter schema (`customer_id`, a string), the input `C1001`, and the card row it returned. The SQL statement appears on the Attributes tab as `db.statement`.

## UI-14: Activity history
**Steps**
1. Go back to the app tab and click **📊 Activity history**.

**Expected**
- **Drafts generated** is 6: Amit, Rahul (balance), Ananya ×2, Suresh and Rahul (card).
- **Account queries** matches the number of account rows in the table.
- **Acceptance rate** is shown as a percentage, not "–".
- The table lists each draft with its sender, subject, intent, data source, action (**ACCEPTED**, **ACCEPTED_WITH_EDITS**, **REJECTED** or **PENDING**), processing time in seconds, and trace ID.
- Ananya's email appears twice: once **REJECTED** and once **PENDING**.

---

## Results
| ID | Test | Result | Notes |
|---|---|---|---|
| UI-01 | Dashboard loads | | |
| UI-02 | Inbox list and email detail | | |
| UI-03 | Inbox status filter | | |
| UI-04 | Non-account → product agent | | |
| UI-05 | Account → auth + core banking | | |
| UI-06 | Duplicate-debit dispute | | |
| UI-07 | Accept as-is | | |
| UI-08 | Accept with edits | | |
| UI-09 | Reject needs a comment | | |
| UI-10 | Re-process rejected email | | |
| UI-11 | Unregistered sender fails auth | | |
| UI-12 | Credit card query | | |
| UI-13 | Agent trace + Phoenix link | | |
| UI-14 | Activity history | | |

**Summary:** _X passed, Y failed, Z blocked._ List each failure with the step number and what you saw.
