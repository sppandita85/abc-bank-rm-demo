"""Postgres helpers (psycopg3 + small connection pool)."""
from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import config

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(config.dsn(), min_size=1, max_size=5,
                               kwargs={"row_factory": dict_row}, open=True)
    return _pool


@contextmanager
def get_conn():
    with get_pool().connection() as conn:
        yield conn


def fetch_all(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [_jsonable(r) for r in cur.fetchall()]


def fetch_one(sql: str, params: tuple | dict | None = None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple | dict | None = None) -> dict | None:
    """Run a write; returns the RETURNING row if any."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone() if cur.description else None
        conn.commit()
        return _jsonable(row) if row else None


def _jsonable(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat(sep=" ", timespec="minutes") if isinstance(v, datetime) else v.isoformat()
        else:
            out[k] = v
    return out


def ping() -> bool:
    try:
        with psycopg.connect(config.dsn(), connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
