"""Database tools used by the agents.

Each lookup is a LangChain tool with a typed, documented signature, so Phoenix shows it as a TOOL span
with its name, description, parameter JSON schema, input arguments, the SQL executed and the rows returned.
Only fixed, parameterised SQL is run; the LLM never writes SQL.
"""
from __future__ import annotations

import json
import re

from langchain_core.tools import BaseTool, tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from openinference.instrumentation.langchain import get_current_span

from db.connection import fetch_all


def _run(t: BaseTool, sql: str, params) -> list[dict]:
    """Execute a tool's SQL and annotate the tool's span with its definition and the query."""
    rows = fetch_all(sql, params)
    span = get_current_span()
    if span is not None:
        definition = convert_to_openai_tool(t)
        span.set_attribute("tool.parameters", json.dumps(definition["function"]["parameters"]))
        span.set_attribute("tool.json_schema", json.dumps(definition))
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", " ".join(sql.split()))
        span.set_attribute("db.row_count", len(rows))
    return rows


# ---------------------------------------------------------------- authentication
@tool(parse_docstring=True)
def lookup_customer_by_email(email: str) -> dict | None:
    """Resolve an email sender to a registered ABC Bank customer (customers table).

    Args:
        email: Sender's email address as received on the RM inbox.
    """
    rows = _run(lookup_customer_by_email,
                """SELECT customer_id, full_name, email, phone, segment, city, kyc_status, rm_name
                   FROM customers WHERE lower(email) = lower(%s)""", (email,))
    return rows[0] if rows else None


# ---------------------------------------------------------------- core banking
@tool(parse_docstring=True)
def get_accounts(customer_id: str) -> list[dict]:
    """Core banking: list the customer's accounts with balance, currency, status and branch.

    Args:
        customer_id: Authenticated customer ID, e.g. C1001.
    """
    return _run(get_accounts,
                """SELECT account_no, account_type, balance, currency, status, branch, ifsc
                   FROM accounts WHERE customer_id = %s ORDER BY account_type""", (customer_id,))


@tool(parse_docstring=True)
def get_recent_transactions(customer_id: str, limit: int = 10) -> list[dict]:
    """Core banking: most recent transactions across all of the customer's accounts, newest first.

    Args:
        customer_id: Authenticated customer ID, e.g. C1001.
        limit: Maximum number of transactions to return.
    """
    return _run(get_recent_transactions,
                """SELECT t.txn_date, t.account_no, t.description, t.amount, t.dr_cr,
                          t.channel, t.status, t.reference_no
                   FROM transactions t JOIN accounts a USING (account_no)
                   WHERE a.customer_id = %s ORDER BY t.txn_date DESC LIMIT %s""", (customer_id, limit))


@tool(parse_docstring=True)
def get_loans(customer_id: str) -> list[dict]:
    """Core banking: customer's loans with outstanding principal, rate, EMI and next EMI date.

    Args:
        customer_id: Authenticated customer ID, e.g. C1001.
    """
    return _run(get_loans,
                """SELECT loan_id, loan_type, principal, outstanding, interest_rate, emi_amount,
                          next_emi_date, tenure_months, emis_paid, status
                   FROM loans WHERE customer_id = %s""", (customer_id,))


@tool(parse_docstring=True)
def get_cards(customer_id: str) -> list[dict]:
    """Core banking: customer's credit cards with limits, outstanding, minimum due, due date and status.

    Args:
        customer_id: Authenticated customer ID, e.g. C1001.
    """
    return _run(get_cards,
                """SELECT card_no_masked, card_type, credit_limit, available_limit, outstanding,
                          min_due, due_date, reward_points, status
                   FROM cards WHERE customer_id = %s""", (customer_id,))


@tool(parse_docstring=True)
def get_fixed_deposits(customer_id: str) -> list[dict]:
    """Core banking: customer's fixed deposits with rate, maturity date, maturity amount and renewal flag.

    Args:
        customer_id: Authenticated customer ID, e.g. C1001.
    """
    return _run(get_fixed_deposits,
                """SELECT fd_no, principal, interest_rate, start_date, maturity_date,
                          maturity_amount, auto_renew, status
                   FROM fixed_deposits WHERE customer_id = %s ORDER BY maturity_date""", (customer_id,))


# ---------------------------------------------------------------- product information
_STOPWORDS = set("""a an the i my me we our you your is are am be to of for in on at and or
    what which how can could would please kindly do does any with this that it its
    hi hello dear sir madam regards thanks thank from about want like just know""".split())


def keywords_from(text: str) -> list[str]:
    return sorted({w for w in re.findall(r"[a-z]+", text.lower()) if w not in _STOPWORDS and len(w) > 2})


@tool(parse_docstring=True)
def search_products(keywords: list[str], category: str | None = None, product_name: str | None = None,
                    max_results: int = 4) -> list[dict]:
    """Search the ABC Bank product catalogue (products table) and return the best-matching products
    with interest rates, fees and charges, eligibility, features and tenure.

    Args:
        keywords: Significant words from the customer's email, used for relevance ranking.
        category: Optional product category, one of SAVINGS, CURRENT, FD, HOME_LOAN, PERSONAL_LOAN, CAR_LOAN, CREDIT_CARD, INVESTMENT, SERVICES.
        product_name: Optional product name mentioned by the customer.
        max_results: Maximum number of products to return.
    """
    catalogue = _run(search_products,
                     """SELECT product_code, product_name, category, interest_rate, fees_charges,
                               eligibility, features, tenure, min_amount, keywords
                        FROM products""", None)
    words = set(keywords)

    def score(p: dict) -> float:
        s = 3.0 if category and p["category"] == category else 0.0
        if product_name and product_name.lower() in p["product_name"].lower():
            s += 5
        return s + len(words & set(keywords_from(f"{p['product_name']} {p['keywords']}")))

    ranked = sorted(((score(p), p) for p in catalogue), key=lambda x: x[0], reverse=True)
    # keep only products reasonably close to the best match
    cutoff = max(1.0, ranked[0][0] * 0.5) if ranked else 1.0
    matches = [p for s, p in ranked if s >= cutoff][:max_results]
    for p in matches:
        p.pop("keywords", None)
    return matches
