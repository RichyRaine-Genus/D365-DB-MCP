"""
D365 MCP Server — discovery tools.

Tools:
  list_d365_instances    — list registered D365 AxDB instances
  list_dmf_views         — list DMF entity export views (BYOD-eligible)
  list_tables            — list base tables matching a name pattern
  search_objects         — search views + tables by keyword
"""

import pyodbc
from mcp_server.config import get_instance, INSTANCES


def _conn(instance_name: str | None) -> pyodbc.Connection:
    cfg = get_instance(instance_name)
    conn_str = (
        f"DRIVER={{{cfg['driver']}}};"
        f"SERVER={cfg['server']};"
        f"DATABASE={cfg['database']};"
        "Trusted_Connection=yes;"
        "ApplicationIntent=ReadOnly;"
    )
    return pyodbc.connect(conn_str, timeout=15)


# ---------------------------------------------------------------------------
# Tool: list_d365_instances
# ---------------------------------------------------------------------------

def list_d365_instances() -> list[dict]:
    """
    Return all registered D365 AxDB instances with their label, server, and
    database name. Useful to know which instances are available before calling
    other tools with an instance= parameter.
    """
    return [
        {
            "instance": key,
            "label": cfg["label"],
            "server": cfg["server"],
            "database": cfg["database"],
            "view_prefixes": cfg["view_prefixes"],
        }
        for key, cfg in INSTANCES.items()
    ]


# ---------------------------------------------------------------------------
# Tool: list_dmf_views
# ---------------------------------------------------------------------------

def list_dmf_views(
    prefix: str | None = None,
    instance: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """
    List DMF entity export views in the target D365 AxDB instance.

    Args:
        prefix:   Optional name prefix filter (e.g. "HCM", "DIR").
                  If omitted, uses all prefixes registered for the instance.
        instance: Instance name from config (default: 'hr').
        limit:    Max rows returned (default 200).

    Returns:
        List of dicts with view_name, schema.
    """
    cfg = get_instance(instance)
    prefixes = [prefix.upper()] if prefix else cfg["view_prefixes"]

    conditions = " OR ".join([f"TABLE_NAME LIKE '{p}%'" for p in prefixes])
    sql = f"""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM   INFORMATION_SCHEMA.VIEWS
        WHERE  TABLE_SCHEMA = 'dbo'
          AND  ({conditions})
        ORDER  BY TABLE_NAME
        OFFSET 0 ROWS FETCH NEXT {int(limit)} ROWS ONLY
    """
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        return [{"schema": row[0], "view_name": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: list_tables
# ---------------------------------------------------------------------------

def list_tables(
    pattern: str | None = None,
    instance: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """
    List base tables in the target D365 AxDB instance, optionally filtered by
    a SQL LIKE pattern (e.g. "HCM%", "%WORKER%").

    Args:
        pattern:  SQL LIKE pattern for TABLE_NAME (default: no filter).
        instance: Instance name (default: 'hr').
        limit:    Max rows returned.

    Returns:
        List of dicts with schema, table_name.
    """
    where = f"AND TABLE_NAME LIKE '{pattern.upper()}'" if pattern else ""
    sql = f"""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM   INFORMATION_SCHEMA.TABLES
        WHERE  TABLE_TYPE = 'BASE TABLE'
          {where}
        ORDER  BY TABLE_NAME
        OFFSET 0 ROWS FETCH NEXT {int(limit)} ROWS ONLY
    """
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        return [{"schema": row[0], "table_name": row[1]} for row in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: search_objects
# ---------------------------------------------------------------------------

def search_objects(
    keyword: str,
    object_types: list[str] | None = None,
    instance: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Search for tables and/or views whose name contains keyword.

    Args:
        keyword:      Text to search for in object name (case-insensitive).
        object_types: List of 'TABLE', 'VIEW', or both (default: both).
        instance:     Instance name (default: 'hr').
        limit:        Max rows returned.

    Returns:
        List of dicts with object_type, schema, object_name.
    """
    types = [t.upper() for t in (object_types or ["TABLE", "VIEW"])]
    type_filter = ", ".join(f"'{t}'" for t in types)

    sql = f"""
        SELECT o.type_desc, SCHEMA_NAME(o.schema_id) AS [schema], o.name
        FROM   sys.objects o
        WHERE  o.type IN ('U', 'V')
          AND  o.type_desc IN ({type_filter.replace('TABLE', 'USER_TABLE').replace('VIEW', 'VIEW')})
          AND  o.name LIKE '%{keyword.upper()}%'
        ORDER  BY o.name
        OFFSET 0 ROWS FETCH NEXT {int(limit)} ROWS ONLY
    """
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        return [
            {"object_type": row[0], "schema": row[1], "object_name": row[2]}
            for row in cur.fetchall()
        ]
    finally:
        conn.close()
