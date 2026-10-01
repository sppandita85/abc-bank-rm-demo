# ABC Bank RM Assistant: UI test results

**Run date:** 29 Sep 2026, about 10:20–10:35 IST
**Precondition:** `python -m db.init_db` run by the operator. After reload, the inbox held 15 emails, all **New**.

| ID | Test | Result | Notes |
|---|---|---|---|
| UI-01 | Dashboard loads | PASS | Header, date, KPIs (15/0/0/0/0s), both tabs, RM card and 3 green health dots all correct. No errors on the page. |
| UI-02 | Inbox list and email detail | PASS | Heading reads "Customer emails (15)" with Rohan Desai at the top. Amit's detail shows prospect.amit@gmail.com and the Rs 90 lakh Pune flat. Info box and Process button shown; card reads Viewing. |
| UI-03 | Inbox status filter | PASS | Approved gives "Customer emails (0)"; All gives 15 again. |
| UI-04 | Non-account → product agent | FAIL (minor) | Everything else passed: chips Intent → Product Information → Drafting; Non-Account / Product Info / N/A; draft has "Dear Amit", 8.35% and the right sign-off; notes box shown; source is the Product Information Database with ABC Home Loan; badges and KPIs (14 / 1) correct. **Failed item:** the progress panel never showed **"Draft ready in Xs"**. It went "Running AI agents…" → "Core Banking complete…" / "Email Drafting complete…", then disappeared when the page re-ran. |
| UI-05 | Account → auth + core banking | **FAIL** | Chips, Account / Balance / SUCCESS, source Core Banking C1001 and the 2-account table were all correct. **Wrong balance in the draft:** it says *"The current available balance in your savings account ending 0001 is Rs 1,84,523.55."* The Accounts table shows **1845230.55** (Rs 18,45,230.55), so the LLM dropped a digit. The full account number isn't in the draft; it's shown as "ending 0001". |
| UI-06 | Duplicate-debit dispute | PASS | Account / Dispute. Suspected Duplicate Debits table has one row: 18999, REF771234501 and REF771234502. Recent Transactions table shown. Draft acknowledges Rs 18,999 and gives no refund timeframe. Notes say "Raise dispute ticket for suspected duplicate debit". |
| UI-07 | Accept as-is | PASS | "Accepted by Priya Sharma on 29 Sep, 10:26". Fields disabled; only Re-process shown. Approved badge; KPIs Approved 1 / Pending 2. |
| UI-08 | Accept with edits | PASS | Before editing: Accept enabled, Accept with edits disabled. After the edit, the caption appeared and the buttons swapped. Banner "Accepted With Edits by Priya Sharma on 29 Sep, 10:27"; P.S. line kept; the original-draft expander doesn't have it; Approved 2, "1 with edits". |
| UI-09 | Reject needs a comment | PASS | An empty comment gives the warning, and the email stays in Pending review. With the comment: "Rejected by Priya Sharma on 29 Sep, 10:28 — Please include the transaction reference numbers". Rejected badge, Re-process button, Rejected KPI 1. |
| UI-10 | Re-process rejected email | FAIL (minor) | New editable draft with Accept, Accept with edits and Reject; badge back to Pending review. **Failed item:** same as UI-04, no "Draft ready in Xs" at the end. |
| UI-11 | Unregistered sender fails auth | PASS | Toast "New email #16 received"; email at the top as New / High; New queries +1. Authentication ✕ in red; Core Banking struck through; Account / NOT_FOUND. Draft asks the sender to write from the registered email or call the branch, with no account data. Retrieved data: "No data was retrieved for this query." |
| UI-12 | Credit card query | PASS | Account / Card / SUCCESS. Cards table has 4532-XXXX-XXXX-1001, ABC Infinite Credit Card. Draft states Rs 1,87,550.00, due 08 Oct 2026. |
| UI-13 | Agent trace + Phoenix link | PASS | Trace ID c41e0be428d300ac571b6072f4739c5e (32 hex characters). 4 agent rows with durations in ms. The intent JSON has intent, sub_intent and method "llm". Phoenix project **abc-bank-rm** shows the tree: rm_email_pipeline → LangGraph → intent_identification_agent (ChatOllama), authentication_agent, core_banking_agent (core_banking.cards), email_drafting_agent (ChatOllama). *Note:* the link opens in a new window (`target=_blank`), so I opened its URL directly in the test browser. |
| UI-14 | Activity history | PASS | Drafts generated 6; Account queries 5, which matches the 5 account rows; Acceptance rate 67%. Table columns are correct; Ananya appears as REJECTED and as PENDING. |

**Summary:** 11 passed, 3 failed, 0 blocked.

- **UI-05, step 2 (major):** the balance in the draft is wrong. It says Rs 1,84,523.55; the database value is Rs 18,45,230.55. The LLM changed a figure it was given, and a customer would receive the wrong balance. Suggested fix: put the formatted amount into the draft from code (a template or post-check) instead of relying on the LLM to copy it.
- **UI-04 and UI-10, step 2 (minor, same cause):** the progress panel never ends on "Draft ready in Xs". Its last state is "Email Drafting complete…", then the page re-runs and the panel is gone. The same thing happened in UI-05, UI-06, UI-11 and UI-12. The status probably needs to be saved in session state so it survives the re-run, or the expected result should be changed.

**Other observations:**
- After re-processing (UI-10), the **Rejected** KPI dropped from 1 to 0, because it counts current status. The history table still records the rejection. This is probably intended; check whether it's what you want.
- During UI-09 the tester's rejection comment went into Ananya's email body by mistake. It was deleted, and the body matched the original draft before the reject was clicked. The Accept button had turned enabled again, which confirms the body was back to the original.
