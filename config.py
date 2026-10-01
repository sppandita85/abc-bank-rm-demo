"""Central settings loaded from environment / .env."""
import os

from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5433"))
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
PG_DB = os.getenv("PG_DB", "abc_bank_rm")
PG_TIMEZONE = os.getenv("PG_TIMEZONE", "Asia/Kolkata")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
PHOENIX_UI_URL = os.getenv("PHOENIX_UI_URL", "http://localhost:6006")
PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT", "abc-bank-rm")

RM_NAME = os.getenv("RM_NAME", "Priya Sharma")
RM_TITLE = os.getenv("RM_TITLE", "Senior Relationship Manager")
BANK_NAME = "ABC Bank"


def dsn(dbname: str | None = None) -> str:
    return (
        f"host={PG_HOST} port={PG_PORT} user={PG_USER} "
        f"password={PG_PASSWORD} dbname={dbname or PG_DB} options='-c timezone={PG_TIMEZONE}'"
    )
