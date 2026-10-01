"""Create the abc_bank_rm database (if needed) and load schema + seed data.

Usage:  python -m db.init_db
"""
from pathlib import Path

import psycopg

import config

HERE = Path(__file__).parent


def main() -> None:
    with psycopg.connect(config.dsn("postgres"), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (config.PG_DB,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{config.PG_DB}"')
            print(f"Created database {config.PG_DB}")

    with psycopg.connect(config.dsn()) as conn:
        conn.execute((HERE / "schema.sql").read_text())
        conn.execute((HERE / "seed.sql").read_text())
        conn.commit()
        for t in ["customers", "accounts", "transactions", "loans", "cards",
                  "fixed_deposits", "products", "emails"]:
            n = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            print(f"  {t:<16} {n:>4} rows")
    print("Database ready.")


if __name__ == "__main__":
    main()
