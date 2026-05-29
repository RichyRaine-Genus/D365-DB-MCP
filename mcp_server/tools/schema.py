"""
D365 MCP Server — schema tools.

Tools:
  get_view_sql           — full SQL text of a named DMF view
  get_view_source_tables — base tables a view reads from (parsed from SQL text)
  get_table_schema       — columns + types for a base table or view
  get_column_count       — count columns in a table/view, with optional name filter
  get_entity_columns     — columns for a DMF entity view with source attribution
  get_custom_fields      — custom fields for a table (GNS* or _CUSTOM suffix)
  get_table_indexes      — indexes defined on a table (PKs, unique, non-unique)
  get_related_tables     — foreign key relationships in and out of a table
"""

import re
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
# Tool: get_view_sql
# ---------------------------------------------------------------------------

def get_view_sql(view_name: str, instance: str | None = None) -> dict:
    """
    Return the full SQL definition of a named DMF view.

    Args:
        view_name: View name (e.g. 'HCMWORKERENTITY', 'CUSTINVOICEJOURNALENTITY').
        instance:  Instance name (default: 'default').

    Returns:
        Dict with view_name, schema, sql_text. sql_text is None if not found.
    """
    sql = """
        SELECT SCHEMA_NAME(o.schema_id), m.definition
        FROM   sys.sql_modules m
        JOIN   sys.objects     o ON o.object_id = m.object_id
        WHERE  o.name = ? AND o.type = 'V'
    """
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql, view_name.upper())
        row = cur.fetchone()
        return {
            "view_name": view_name.upper(),
            "schema": row[0] if row else None,
            "sql_text": row[1] if row else None,
            "found": row is not None,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_view_source_tables
# ---------------------------------------------------------------------------

def get_view_source_tables(view_name: str, instance: str | None = None) -> dict:
    """
    Parse the SQL definition of a view and return the base AxDB tables it reads from.

    Uses a heuristic regex (FROM / JOIN clause extraction).
    Temp tables and CTEs are excluded.

    Args:
        view_name: View name (e.g. 'HCMWORKERENTITY', 'SALESORDERHEADERENTITY').
        instance:  Instance name (default: 'default').

    Returns:
        Dict with view_name, source_tables (list of dicts with table_name, alias).
    """
    view = get_view_sql(view_name, instance)
    if not view["found"]:
        return {"view_name": view_name.upper(), "source_tables": [], "found": False}

    sql_text = view["sql_text"] or ""

    # Extract FROM/JOIN targets: "FROM TableName T0" or "JOIN TableName T1 ON ..."
    pattern = re.compile(
        r'\b(?:FROM|JOIN)\s+([A-Z_][A-Z0-9_]*)\s+([A-Z_][A-Z0-9_]*)',
        re.IGNORECASE,
    )
    SQL_KEYWORDS = {
        "SELECT", "WHERE", "AND", "OR", "ON", "SET", "WITH", "AS",
        "INNER", "LEFT", "RIGHT", "OUTER", "CROSS", "FULL", "LATERAL",
        "APPLY", "PIVOT", "UNPIVOT", "TOP", "DISTINCT", "GROUP", "ORDER",
        "HAVING", "UNION", "EXCEPT", "INTERSECT", "CASE", "WHEN", "THEN",
        "ELSE", "END", "OVER", "PARTITION", "BY",
    }

    seen: dict[str, str] = {}  # table_name → alias
    for match in pattern.finditer(sql_text):
        tbl, alias = match.group(1).upper(), match.group(2).upper()
        if (
            tbl not in SQL_KEYWORDS
            and not tbl.startswith("#")
            and len(tbl) >= 8
        ):
            seen[tbl] = alias

    return {
        "view_name": view_name.upper(),
        "found": True,
        "source_tables": [
            {"table_name": tbl, "alias": alias} for tbl, alias in seen.items()
        ],
    }


# ---------------------------------------------------------------------------
# Tool: get_table_schema
# ---------------------------------------------------------------------------

def get_table_schema(
    object_name: str,
    instance: str | None = None,
) -> dict:
    """
    Return the column schema for a named table or view.

    Args:
        object_name: Table or view name (e.g. 'HCMWORKER', 'CUSTTABLE', 'INVENTTABLE').
        instance:    Instance name (default: 'default').

    Returns:
        Dict with object_name, object_type, columns list of dicts:
          column_name, ordinal, data_type, max_length, precision, scale, is_nullable
    """
    sql = """
        SELECT c.COLUMN_NAME, c.ORDINAL_POSITION, c.DATA_TYPE,
               c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION,
               c.NUMERIC_SCALE, c.IS_NULLABLE, t.TABLE_TYPE
        FROM   INFORMATION_SCHEMA.COLUMNS c
        JOIN   INFORMATION_SCHEMA.TABLES  t
               ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
        WHERE  c.TABLE_NAME = ?
        ORDER  BY c.ORDINAL_POSITION
    """
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql, object_name.upper())
        rows = cur.fetchall()
        return {
            "object_name": object_name.upper(),
            "object_type": rows[0][7] if rows else None,
            "found": bool(rows),
            "column_count": len(rows),
            "columns": [
                {
                    "column_name": r[0],
                    "ordinal": r[1],
                    "data_type": r[2],
                    "max_length": r[3],
                    "precision": r[4],
                    "scale": r[5],
                    "is_nullable": r[6] == "YES",
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_entity_columns
# ---------------------------------------------------------------------------

def get_entity_columns(view_name: str, instance: str | None = None) -> dict:
    """
    Return columns for a DMF entity view, annotated with whether each column
    name appears in any of the view's source tables (source attribution).

    This combines get_view_sql + get_view_source_tables + get_table_schema.

    Args:
        view_name: DMF entity view name (e.g. 'HCMWORKERENTITY', 'SALESORDERHEADERENTITY').
        instance:  Instance name (default: 'default').

    Returns:
        Dict with view_name, columns (column_name, found_in_source_tables list),
        source_tables list.
    """
    schema_result = get_table_schema(view_name, instance)
    if not schema_result["found"]:
        return {"view_name": view_name.upper(), "found": False, "columns": []}

    source_result = get_view_source_tables(view_name, instance)
    source_tables = [s["table_name"] for s in source_result["source_tables"]]

    # For each source table, collect its column names
    source_col_map: dict[str, set[str]] = {}
    for tbl in source_tables:
        tbl_schema = get_table_schema(tbl, instance)
        source_col_map[tbl] = {
            c["column_name"].upper() for c in tbl_schema.get("columns", [])
        }

    # Annotate each view column with which source tables contain a matching name
    annotated = []
    for col in schema_result["columns"]:
        col_upper = col["column_name"].upper()
        found_in = [
            tbl for tbl, cols in source_col_map.items() if col_upper in cols
        ]
        annotated.append({**col, "found_in_source_tables": found_in})

    return {
        "view_name": view_name.upper(),
        "found": True,
        "column_count": len(annotated),
        "source_tables": source_tables,
        "columns": annotated,
    }


# ---------------------------------------------------------------------------
# Tool: get_custom_fields
# ---------------------------------------------------------------------------

def get_custom_fields(
    table_name: str,
    instance: str | None = None,
) -> dict:
    """
    Return custom fields for a named table — columns whose name starts with
    a GNS* prefix or ends with _CUSTOM suffix.

    Args:
        table_name: Table name (e.g. 'HCMWORKER', 'CUSTTABLE', 'INVENTTABLE').
        instance:   Instance name (default: 'default').

    Returns:
        Dict with table_name, custom_field_count, custom_fields list.
    """
    sql = """
        SELECT c.name, t.name AS data_type, c.max_length, c.is_nullable
        FROM   sys.columns  c
        JOIN   sys.types    t  ON t.user_type_id = c.user_type_id
        JOIN   sys.objects  o  ON o.object_id = c.object_id
        WHERE  o.name = ?
          AND  (c.name LIKE 'GNS%' OR c.name LIKE '%_CUSTOM')
        ORDER  BY c.column_id
    """
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql, table_name.upper())
        rows = cur.fetchall()
        return {
            "table_name": table_name.upper(),
            "custom_field_count": len(rows),
            "custom_fields": [
                {
                    "column_name": r[0],
                    "data_type": r[1],
                    "max_length": r[2],
                    "is_nullable": r[3],
                    "pattern": "GNS_prefix" if r[0].upper().startswith("GNS") else "_CUSTOM_suffix",
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_column_count
# ---------------------------------------------------------------------------

def get_column_count(
    object_name: str,
    name_filter: str | None = None,
    instance: str | None = None,
) -> dict:
    """
    Return the number of columns in a D365 AxDB table or view.

    Optionally filter by a SQL LIKE pattern on the column name, e.g.:
      name_filter = "GNS%"      — count only GNS custom columns
      name_filter = "%DATE%"    — count date-related columns
      name_filter = "%ID"       — count ID / foreign key columns

    Args:
        object_name:  Table or view name (e.g. 'HCMPOSITION', 'INVENTTABLE').
        name_filter:  Optional SQL LIKE pattern on column name (case-insensitive).
        instance:     Instance name (default: 'default').

    Returns:
        Dict with object_name, name_filter, total_column_count, filtered_column_count,
        and a breakdown by data_type.
    """
    where_filter = f"AND c.COLUMN_NAME LIKE '{name_filter.upper()}'" if name_filter else ""

    sql = f"""
        SELECT c.COLUMN_NAME, c.DATA_TYPE
        FROM   INFORMATION_SCHEMA.COLUMNS c
        JOIN   INFORMATION_SCHEMA.TABLES  t
               ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
        WHERE  c.TABLE_NAME = ?
        {where_filter}
        ORDER  BY c.ORDINAL_POSITION
    """

    # Also get total unfiltered count
    total_sql = """
        SELECT COUNT(*)
        FROM   INFORMATION_SCHEMA.COLUMNS
        WHERE  TABLE_NAME = ?
    """

    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql, object_name.upper())
        rows = cur.fetchall()

        cur.execute(total_sql, object_name.upper())
        total = cur.fetchone()[0]

        # Breakdown by data type
        type_counts: dict[str, int] = {}
        for r in rows:
            dt = r[1].lower()
            type_counts[dt] = type_counts.get(dt, 0) + 1

        return {
            "object_name": object_name.upper(),
            "name_filter": name_filter or None,
            "total_column_count": total,
            "filtered_column_count": len(rows),
            "by_data_type": type_counts,
            "column_names": [r[0] for r in rows],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_table_indexes
# ---------------------------------------------------------------------------

def get_table_indexes(
    table_name: str,
    instance: str | None = None,
) -> dict:
    """
    Return all indexes defined on a D365 AxDB table.

    Includes primary keys, unique indexes, and non-unique indexes, along with
    the columns they cover. Useful for understanding clustered keys, RECID
    indexes, and query performance characteristics.

    Args:
        table_name: Table name (e.g. 'HCMWORKER', 'INVENTTRANS').
        instance:   Instance name (default: 'default').

    Returns:
        Dict with table_name, index_count, indexes (list of dicts with
        index_name, type, is_unique, is_primary_key, columns list).
    """
    sql = """
        SELECT
            i.name                              AS index_name,
            i.type_desc                         AS index_type,
            i.is_unique,
            i.is_primary_key,
            c.name                              AS column_name,
            ic.key_ordinal,
            ic.is_descending_key
        FROM   sys.indexes      i
        JOIN   sys.index_columns ic ON ic.object_id = i.object_id
                                   AND ic.index_id   = i.index_id
        JOIN   sys.columns      c  ON c.object_id    = i.object_id
                                   AND c.column_id    = ic.column_id
        JOIN   sys.objects      o  ON o.object_id     = i.object_id
        WHERE  o.name = ?
          AND  o.type = 'U'
          AND  i.type > 0          -- exclude heap (0)
        ORDER  BY i.name, ic.key_ordinal
    """

    conn = _conn(instance)
    try:
        cur = conn.cursor()
        cur.execute(sql, table_name.upper())
        rows = cur.fetchall()

        # Group columns by index
        indexes: dict[str, dict] = {}
        for r in rows:
            idx_name = r[0]
            if idx_name not in indexes:
                indexes[idx_name] = {
                    "index_name": idx_name,
                    "index_type": r[1],
                    "is_unique": bool(r[2]),
                    "is_primary_key": bool(r[3]),
                    "columns": [],
                }
            indexes[idx_name]["columns"].append({
                "column_name": r[4],
                "key_ordinal": r[5],
                "descending": bool(r[6]),
            })

        index_list = list(indexes.values())
        return {
            "table_name": table_name.upper(),
            "found": bool(index_list),
            "index_count": len(index_list),
            "indexes": index_list,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: get_related_tables
# ---------------------------------------------------------------------------

def get_related_tables(
    table_name: str,
    instance: str | None = None,
) -> dict:
    """
    Return foreign key relationships for a D365 AxDB table.

    Returns two lists:
      - outbound: FK constraints WHERE this table references another table
                  (i.e. columns in this table that are FKs into other tables)
      - inbound:  FK constraints WHERE other tables reference this table
                  (i.e. this table is the parent / lookup target)

    Useful for tracing D365 data model relationships, e.g. finding all
    tables that join to HCMWORKER, or what reference tables SALESTABLE uses.

    Args:
        table_name: Table name (e.g. 'HCMWORKER', 'CUSTTABLE').
        instance:   Instance name (default: 'default').

    Returns:
        Dict with table_name, outbound (FK to other tables),
        inbound (other tables FK to this table).
    """
    outbound_sql = """
        SELECT
            fk.name                             AS fk_name,
            tp.name                             AS parent_table,
            cp.name                             AS parent_column,
            tr.name                             AS referenced_table,
            cr.name                             AS referenced_column
        FROM   sys.foreign_keys        fk
        JOIN   sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN   sys.objects             tp  ON tp.object_id = fk.parent_object_id
        JOIN   sys.columns             cp  ON cp.object_id = fk.parent_object_id
                                          AND cp.column_id = fkc.parent_column_id
        JOIN   sys.objects             tr  ON tr.object_id = fk.referenced_object_id
        JOIN   sys.columns             cr  ON cr.object_id = fk.referenced_object_id
                                          AND cr.column_id = fkc.referenced_column_id
        WHERE  tp.name = ?
        ORDER  BY tr.name, fk.name
    """

    inbound_sql = """
        SELECT
            fk.name                             AS fk_name,
            tp.name                             AS child_table,
            cp.name                             AS child_column,
            tr.name                             AS this_table,
            cr.name                             AS this_column
        FROM   sys.foreign_keys        fk
        JOIN   sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
        JOIN   sys.objects             tp  ON tp.object_id = fk.parent_object_id
        JOIN   sys.columns             cp  ON cp.object_id = fk.parent_object_id
                                          AND cp.column_id = fkc.parent_column_id
        JOIN   sys.objects             tr  ON tr.object_id = fk.referenced_object_id
        JOIN   sys.columns             cr  ON cr.object_id = fk.referenced_object_id
                                          AND cr.column_id = fkc.referenced_column_id
        WHERE  tr.name = ?
        ORDER  BY tp.name, fk.name
    """

    conn = _conn(instance)
    try:
        cur = conn.cursor()
        tbl = table_name.upper()

        cur.execute(outbound_sql, tbl)
        outbound = [
            {
                "fk_name": r[0],
                "from_column": r[2],
                "to_table": r[3],
                "to_column": r[4],
            }
            for r in cur.fetchall()
        ]

        cur.execute(inbound_sql, tbl)
        inbound = [
            {
                "fk_name": r[0],
                "from_table": r[1],
                "from_column": r[2],
                "to_column": r[4],
            }
            for r in cur.fetchall()
        ]

        return {
            "table_name": tbl,
            "outbound_fk_count": len(outbound),
            "inbound_fk_count": len(inbound),
            "outbound": outbound,   # this table → other tables
            "inbound": inbound,     # other tables → this table
        }
    finally:
        conn.close()
