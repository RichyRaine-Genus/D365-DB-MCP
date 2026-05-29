"""
Quick connection test — run this to verify your AxDB connection is working.

Queries sys.tables (generic) so it works regardless of which D365 modules are
configured. No assumption is made about which value stream the database serves.

Usage:
    .venv\\Scripts\\python.exe tools\\connection_test.py
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

    cur.execute("SELECT COUNT(*) FROM sys.tables")
    count = cur.fetchone()[0]
    print(f"Total tables in AxDB: {count}")

    # Quick sanity-check: confirm this looks like a D365 AxDB
    # (SYSTEMPARAMETERS is present in every D365 / F&O database)
    cur.execute(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_NAME = 'SYSTEMPARAMETERS'"
    )
    is_d365 = cur.fetchone()[0] > 0
    print(f"Looks like D365 AxDB: {'Yes' if is_d365 else 'No (SYSTEMPARAMETERS not found)'}")

    conn.close()
    print("OK")

except Exception as e:
    print(f"FAILED: {e}", file=sys.stderr)
    sys.exit(1)
