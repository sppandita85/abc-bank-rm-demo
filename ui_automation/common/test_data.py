"""Known seed data (db/seed.sql) and expected values used by the UI tests."""

SEEDED_EMAIL_COUNT = 15
NEWEST_EMAIL_ID = 15            # Rohan Desai – top of the inbox

RAHUL_BALANCE = {"id": 1, "sender": "Rahul Mehta", "subject": "Current balance in my savings account"}
AMIT_HOME_LOAN = {"id": 2, "sender": "Amit Verma", "email": "prospect.amit@gmail.com",
                  "subject": "Home loan interest rates"}
ANANYA_DISPUTE = {"id": 3, "sender": "Ananya Iyer", "subject": "Amount debited twice - Croma purchase"}
FATIMA_CARD = {"id": 9, "sender": "Fatima Sheikh", "subject": "Credit card blocked?"}

RAHUL_SAVINGS_BALANCE = "18,45,230.55"
RAHUL_SAVINGS_ACCOUNT_NO = "50100012340001"

UNREGISTERED_SENDER = {
    "name": "Suresh Pillai", "email": "unknown.person@gmail.com", "subject": "My account balance",
    "body": "Hi, please tell me the balance in my savings account. Thanks, Suresh", "priority": "HIGH",
}

UI_TIMEOUT = 20        # seconds for normal page updates
LLM_TIMEOUT = 180      # seconds for "Process with AI agents" (local llama3.1)
