"""
Central database connection config.

All scripts that need live AxDB access should import get_axdb_conn() from here.
Credentials: Windows Authentication (Trusted_Connection) — no secrets in source.

Configuration precedence (highest to lowest):
  1. OS environment variables  AXDB_SERVER / AXDB_DATABASE / AXDB_DRIVER
  2. A .env file  (loaded natively via python-dotenv, never overriding real env vars)
  3. Hardcoded fallback defaults below

.env search order (each existing file loaded with override=False):
  1. explicit path from the AXDB_DOTENV environment variable
  2. the current working directory
  3. the repo root (resolved relative to this module)

Each developer should create a .env file in the repo root with their own values:

    # .env  (gitignored — never commit this file)
    AXDB_SERVER=GNSPLC-DEV-123        # your Tier 1 DEV machine name
    AXDB_DATABASE=AxDB
    AXDB_DRIVER=ODBC Driver 17 for SQL Server

Copy .env.example to .env to get started.
"""

import os
from pathlib import Path

import pyodbc


def _load_dotenv_files() -> None:
    """Populate os.environ from a .env without overriding real env vars.

    Precedence: OS env > .env > defaults. Search order:
      1. explicit path from AXDB_DOTENV
      2. current working directory
      3. repo root (relative to this module)
    Missing files are a silent no-op; python-dotenv absent is a no-op.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    explicit = os.environ.get("AXDB_DOTENV")
    if explicit:
        load_dotenv(explicit, override=False)
        return
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[0] / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


_load_dotenv_files()

# ── Connection parameters ─────────────────────────────────────────────────────
# Each can be overridden via .env or environment variable.
AXDB_SERVER   = os.environ.get("AXDB_SERVER") or "GNSPLC-DEV-283"
AXDB_DATABASE = os.environ.get("AXDB_DATABASE") or "AxDB"
AXDB_DRIVER   = os.environ.get("AXDB_DRIVER") or "ODBC Driver 17 for SQL Server"
AXDB_AUTH_MODE = (os.environ.get("AXDB_AUTH_MODE") or "windows").strip().lower()
AXDB_USERNAME = os.environ.get("AXDB_USERNAME") or ""
AXDB_PASSWORD = os.environ.get("AXDB_PASSWORD") or ""


def _build_conn_str(server: str, database: str, driver: str) -> str:
    if AXDB_AUTH_MODE == "sql" or (AXDB_USERNAME and AXDB_PASSWORD):
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={AXDB_USERNAME};"
            f"PWD={AXDB_PASSWORD};"
            "ApplicationIntent=ReadOnly;"
        )

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "ApplicationIntent=ReadOnly;"
    )


def get_axdb_conn(
    server: str | None = None,
    database: str | None = None,
    driver: str | None = None,
) -> pyodbc.Connection:
    """
    Return an open pyodbc connection to AxDB.
    Caller is responsible for closing it.

    Parameters override the .env / environment variable values for that call only,
    which allows the MCP server to support multiple instances in the same process.
    """
    conn_str = _build_conn_str(
        server   or AXDB_SERVER,
        database or AXDB_DATABASE,
        driver   or AXDB_DRIVER,
    )
    return pyodbc.connect(conn_str, timeout=15)


def axdb_conn_str(
    server: str | None = None,
    database: str | None = None,
    driver: str | None = None,
) -> str:
    """Return the raw ODBC connection string (useful for pandas.read_sql / SQLAlchemy URL)."""
    return _build_conn_str(
        server   or AXDB_SERVER,
        database or AXDB_DATABASE,
        driver   or AXDB_DRIVER,
    )
