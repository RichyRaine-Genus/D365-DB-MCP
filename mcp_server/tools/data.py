"""
D365 MCP Server — data inspection tools.

Tools:
  get_row_count      — count rows in a table/view, with optional WHERE filter
  get_data_sample    — return top N rows from a table/view, with optional WHERE filter
  get_distinct_values — distinct values in a column (great for status / enum fields)
"""

import pyodbc
from mcp_server.config import get_instance


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
# Tool: get_row_count
# ---------------------------------------------------------------------------

def get_row_count(
    table_name: str,
    where_clause: str | None = None,
    instance: str | None = None,
) -> dict:
    """
    Return the row count for a D365 AxDB table or view.

    Supports an optional WHERE clause for conditional counts, e.g.:
      where_clause = "EMPLSTATUS = 1"           — active workers
      where_clause = "DATAAREAID = 'GBSI'"      — rows for a specific legal entity
      where_clause = "CREATEDDATETIME >= '2024-01-01'"  — rows since a date

    Args:
        table_name:   Table or view name (e.g. 'HCMWORKER', 'CUSTTABLE').
        where_clause: Optional SQL WHERE clause (without the WHERE keyword).
                      Internal use only — not sanitised for untrusted input.
        instance:     Instance name (default: 'default').

    Returns:
        Dict with table_name, where_clause, row_count.
    """
    where_sql = f"WHERE {where_clause}" if where_clause else ""
    sql = f"SELECT COUNT(*) FROM {table_name.upper()} {where_sql}"

    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        count = cur.fetchone()[0]
        return {
            "table_name": table_name.upper(),
            "where_clause": where_clause or None,
            "row_count": count,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_data_sample
# ---------------------------------------------------------------------------

def get_data_sample(
    table_name: str,
    top: int = 10,
    where_clause: str | None = None,
    columns: list[str] | None = None,
    order_by: str | None = None,
    instance: str | None = None,
) -> dict:
    """
    Return a sample of rows from a D365 AxDB table or view.

    Useful for understanding the shape and content of a table without
    needing to write SQL manually.

    Args:
        table_name:   Table or view name (e.g. 'HCMWORKER', 'INVENTTABLE').
        top:          Number of rows to return (default 10, max 200).
        where_clause: Optional SQL WHERE clause (without the WHERE keyword),
                      e.g. "DATAAREAID = 'GBSI'" or "EMPLSTATUS = 1".
        columns:      Optional list of column names to include. Default: all columns.
        order_by:     Optional ORDER BY expression, e.g. 'CREATEDDATETIME DESC'.
        instance:     Instance name (default: 'default').

    Returns:
        Dict with table_name, row_count (returned), columns, rows (list of dicts).
    """
    top = min(int(top), 200)
    col_sql = ", ".join(c.upper() for c in columns) if columns else "*"
    where_sql = f"WHERE {where_clause}" if where_clause else ""
    order_sql = f"ORDER BY {order_by}" if order_by else ""

    sql = f"""
        SELECT TOP {top} {col_sql}
        FROM   {table_name.upper()}
        {where_sql}
        {order_sql}
    """

    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        col_names = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return {
            "table_name": table_name.upper(),
            "where_clause": where_clause or None,
            "columns_returned": col_names,
            "row_count": len(rows),
            "rows": [dict(zip(col_names, row)) for row in rows],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_distinct_values
# ---------------------------------------------------------------------------

def get_distinct_values(
    table_name: str,
    column_name: str,
    limit: int = 100,
    where_clause: str | None = None,
    include_counts: bool = True,
    instance: str | None = None,
) -> dict:
    """
    Return distinct values for a column in a D365 AxDB table or view.

    Essential for understanding status fields, type enumerations, and
    reference data — e.g. what EMPLSTATUS values exist in HCMWORKER,
    or what DATAAREAID values are present in a table.

    Args:
        table_name:     Table or view name (e.g. 'HCMWORKER').
        column_name:    Column to inspect (e.g. 'EMPLSTATUS', 'DATAAREAID').
        limit:          Max distinct values to return (default 100).
        where_clause:   Optional SQL WHERE clause to pre-filter before grouping.
        include_counts: If True (default), include the row count per value.
        instance:       Instance name (default: 'default').

    Returns:
        Dict with table_name, column_name, distinct_count, values
        (list of dicts with value and optionally row_count).
    """
    where_sql = f"WHERE {where_clause}" if where_clause else ""

    if include_counts:
        sql = f"""
            SELECT TOP {int(limit)} {column_name.upper()}, COUNT(*) AS row_count
            FROM   {table_name.upper()}
            {where_sql}
            GROUP  BY {column_name.upper()}
            ORDER  BY COUNT(*) DESC
        """
    else:
        sql = f"""
            SELECT DISTINCT TOP {int(limit)} {column_name.upper()}
            FROM   {table_name.upper()}
            {where_sql}
            ORDER  BY {column_name.upper()}
        """

    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()

        if include_counts:
            values = [{"value": r[0], "row_count": r[1]} for r in rows]
        else:
            values = [{"value": r[0]} for r in rows]

        return {
            "table_name": table_name.upper(),
            "column_name": column_name.upper(),
            "where_clause": where_clause or None,
            "distinct_count": len(values),
            "values": values,
        }
    finally:
        conn.close()
