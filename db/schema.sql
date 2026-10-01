-- ABC Bank RM Assistant schema
DROP TABLE IF EXISTS email_responses, emails, transactions, fixed_deposits, cards, loans,
    accounts, products, customers CASCADE;

-- ---------- Core banking ----------
CREATE TABLE customers (
    customer_id   VARCHAR(10) PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    phone         VARCHAR(20),
    segment       VARCHAR(20),          -- Premier / Priority / Classic
    city          VARCHAR(50),
    kyc_status    VARCHAR(20) DEFAULT 'VERIFIED',
    rm_name       VARCHAR(100),
    created_at    TIMESTAMP DEFAULT now()
);

CREATE TABLE accounts (
    account_no     VARCHAR(20) PRIMARY KEY,
    customer_id    VARCHAR(10) REFERENCES customers(customer_id),
    account_type   VARCHAR(20),          -- SAVINGS / CURRENT / SALARY
    balance        NUMERIC(14,2),
    currency       VARCHAR(3) DEFAULT 'INR',
    status         VARCHAR(20) DEFAULT 'ACTIVE',
    branch         VARCHAR(60),
    ifsc           VARCHAR(15),
    opened_on      DATE
);

CREATE TABLE transactions (
    txn_id         SERIAL PRIMARY KEY,
    account_no     VARCHAR(20) REFERENCES accounts(account_no),
    txn_date       TIMESTAMP,
    description    VARCHAR(200),
    amount         NUMERIC(14,2),
    dr_cr          CHAR(2),              -- DR / CR
    channel        VARCHAR(20),          -- UPI / NEFT / IMPS / ATM / POS / CHQ
    status         VARCHAR(20) DEFAULT 'SUCCESS',
    reference_no   VARCHAR(30),
    balance_after  NUMERIC(14,2)
);

CREATE TABLE loans (
    loan_id          VARCHAR(20) PRIMARY KEY,
    customer_id      VARCHAR(10) REFERENCES customers(customer_id),
    loan_type        VARCHAR(30),
    principal        NUMERIC(14,2),
    outstanding      NUMERIC(14,2),
    interest_rate    NUMERIC(5,2),
    emi_amount       NUMERIC(12,2),
    next_emi_date    DATE,
    tenure_months    INT,
    emis_paid        INT,
    status           VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE cards (
    card_no_masked   VARCHAR(25) PRIMARY KEY,
    customer_id      VARCHAR(10) REFERENCES customers(customer_id),
    card_type        VARCHAR(30),
    credit_limit     NUMERIC(12,2),
    available_limit  NUMERIC(12,2),
    outstanding      NUMERIC(12,2),
    min_due          NUMERIC(12,2),
    due_date         DATE,
    reward_points    INT,
    status           VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE fixed_deposits (
    fd_no            VARCHAR(20) PRIMARY KEY,
    customer_id      VARCHAR(10) REFERENCES customers(customer_id),
    principal        NUMERIC(14,2),
    interest_rate    NUMERIC(5,2),
    start_date       DATE,
    maturity_date    DATE,
    maturity_amount  NUMERIC(14,2),
    auto_renew       BOOLEAN DEFAULT FALSE,
    status           VARCHAR(20) DEFAULT 'ACTIVE'
);

-- ---------- Product information ----------
CREATE TABLE products (
    product_code   VARCHAR(12) PRIMARY KEY,
    product_name   VARCHAR(100) NOT NULL,
    category       VARCHAR(30),          -- SAVINGS / CURRENT / FD / HOME_LOAN / PERSONAL_LOAN / CAR_LOAN / CREDIT_CARD / INVESTMENT
    interest_rate  TEXT,
    fees_charges   TEXT,
    eligibility    TEXT,
    features       TEXT,
    tenure         TEXT,
    min_amount     TEXT,
    keywords       TEXT
);

-- ---------- RM workflow ----------
CREATE TABLE emails (
    email_id      SERIAL PRIMARY KEY,
    from_email    VARCHAR(150) NOT NULL,
    from_name     VARCHAR(100),
    subject       VARCHAR(250),
    body          TEXT,
    received_at   TIMESTAMP DEFAULT now(),
    priority      VARCHAR(10) DEFAULT 'NORMAL',
    status        VARCHAR(20) DEFAULT 'NEW'   -- NEW / PENDING_REVIEW / APPROVED / REJECTED
);

CREATE TABLE email_responses (
    response_id     SERIAL PRIMARY KEY,
    email_id        INT REFERENCES emails(email_id) ON DELETE CASCADE,
    intent          VARCHAR(20),
    sub_intent      VARCHAR(40),
    confidence      NUMERIC(4,2),
    customer_id     VARCHAR(10),
    auth_status     VARCHAR(20),
    data_source     VARCHAR(40),
    retrieved_data  JSONB,
    draft_subject   VARCHAR(250),
    draft_body      TEXT,
    internal_notes  TEXT,
    final_subject   VARCHAR(250),
    final_body      TEXT,
    rm_action       VARCHAR(25),            -- ACCEPTED / REJECTED / ACCEPTED_WITH_EDITS
    rm_comment      TEXT,
    agent_trace     JSONB,
    trace_id        VARCHAR(64),
    processing_ms   INT,
    created_at      TIMESTAMP DEFAULT now(),
    actioned_at     TIMESTAMP
);

CREATE INDEX idx_txn_account ON transactions(account_no, txn_date DESC);
CREATE INDEX idx_resp_email ON email_responses(email_id);
