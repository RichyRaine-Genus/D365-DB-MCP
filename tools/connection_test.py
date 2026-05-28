"""
Quick connection test — run this to verify your AxDB connection is working.

Usage:
    .\.venv\Scripts\python.exe tools\connection_test.py
"""

import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_config import get_axdb_conn, AXDB_SERVER, AXDB_DATABASE

print(f"Connecting to {AXDB_SERVER} / {AXDB_DATABASE} ...")

try:
    conn = get_axdb_conn()
    cur = conn.cursor()

    cur.execute("SELECT @@VERSION")
    version = cur.fetchone()[0].splitlines()[0]
    print(f"SQL Server version: {version}")

    cur.execute("SELECT COUNT(*) FROM HCMWORKER")
    count = cur.fetchone()[0]
    print(f"HCMWORKER row count: {count}")

    conn.close()
    print("OK")

except Exception as e:
    print(f"FAILED: {e}", file=sys.stderr)
    sys.exit(1)
