"""
D365 MCP Server — main entry point.

Run in stdio mode (for VS Code Copilot / Claude Desktop):
    python -m mcp_server.server

Requires:  pip install mcp
"""

import sys
import json
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from mcp_server.tools.discovery import (
    list_d365_instances,
    list_dmf_views,
    list_tables,
    search_objects,
    search_by_column,
)
from mcp_server.tools.schema import (
    get_view_sql,
    get_view_source_tables,
    get_view_dependencies,
    get_table_schema,
    get_column_count,
    get_entity_columns,
    get_custom_fields,
    get_table_indexes,
    get_related_tables,
)
from mcp_server.tools.data import (
    get_row_count,
    get_data_sample,
    get_distinct_values,
)

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
log = logging.getLogger(__name__)

app = Server("d365-axdb")


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_d365_instances",
            description=(
                "List all registered D365 AxDB instances (HR, Finance, SCM). "
                "Use this first to discover which instance= values are available."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list_dmf_views",
            description=(
                "List DMF entity export views in a D365 AxDB instance. "
                "These are the views that BYOD exports use as sources. "
                "Covers all value streams: HR (HCM), Finance (LEDGER/CUST/VEND), SCM (INVENT/PURCH/SALES/WHS), Projects (PROJ), etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": (
                            "Optional module prefix filter, e.g. 'HCM' (HR), 'LEDGER' (Finance), "
                            "'CUST' (AR), 'VEND' (AP), 'INVENT' (Inventory), 'PURCH' (Procurement), "
                            "'SALES' (Sales), 'WHS' (Warehouse), 'PROJ' (Projects). "
                            "Omit to return views across all configured modules."
                        ),
                    },
                    "instance": {
                        "type": "string",
                        "description": "Instance name (default: 'default'). Use list_d365_instances to see available options.",
                    },
                    "limit": {"type": "integer", "description": "Max results (default 200)"},
                },
            },
        ),
        types.Tool(
            name="list_tables",
            description=(
                "List base tables in a D365 AxDB instance matching an optional SQL LIKE pattern. "
                "Works across all D365 modules — HR, Finance, SCM, Projects, etc."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": (
                            "SQL LIKE pattern for the table name, e.g. 'HCM%' (HR), "
                            "'LEDGER%' (GL), 'INVENT%' (Inventory), 'CUST%' (AR), "
                            "'VEND%' (AP), 'SALES%' (Sales), '%WORKER%' (any worker table)."
                        ),
                    },
                    "instance": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        ),
        types.Tool(
            name="search_objects",
            description="Search for tables and views by keyword in their name.",
            inputSchema={
                "type": "object",
                "required": ["keyword"],
                "properties": {
                    "keyword": {"type": "string"},
                    "object_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["TABLE", "VIEW"]},
                        "description": "Filter by object type. Default: both.",
                    },
                    "instance": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        ),
        types.Tool(
            name="search_by_column",
            description=(
                "Find all D365 AxDB tables and/or views that contain a specific column name. "
                "Use this to discover which entities expose a field — e.g. 'LEGALENTITY', "
                "'DATAAREAID', 'WORKER', 'INVOICEID'. Works across all modules."
            ),
            inputSchema={
                "type": "object",
                "required": ["column_name"],
                "properties": {
                    "column_name": {
                        "type": "string",
                        "description": "Exact column name to search for (case-insensitive), e.g. 'LEGALENTITY'.",
                    },
                    "object_types": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["TABLE", "VIEW"]},
                        "description": "Filter by object type. Default: both.",
                    },
                    "name_filter": {
                        "type": "string",
                        "description": "SQL LIKE filter on object name, e.g. '%ENTITY%' to restrict to DMF entity views.",
                    },
                    "instance": {"type": "string"},
                    "limit": {"type": "integer", "description": "Max results (default 500)."},
                },
            },
        ),
        types.Tool(
            name="get_view_sql",
            description=(
                "Return the full SQL definition of a named DMF entity view from D365 AxDB. "
                "Supports views from any D365 module (HR, Finance, SCM, Projects, etc.)."
            ),
            inputSchema={
                "type": "object",
                "required": ["view_name"],
                "properties": {
                    "view_name": {
                        "type": "string",
                        "description": (
                            "DMF view name in UPPERCASE, e.g. 'HCMWORKERENTITY' (HR), "
                            "'CUSTINVOICEJOURNALENTITY' (Finance), 'INVENTTABLEENTITY' (SCM)."
                        ),
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_view_source_tables",
            description=(
                "Parse a D365 DMF view's SQL and return the base AxDB tables it reads from, "
                "with their aliases. Uses a heuristic regex — fast but may miss CTEs or subqueries. "
                "Use get_view_dependencies for authoritative results."
            ),
            inputSchema={
                "type": "object",
                "required": ["view_name"],
                "properties": {
                    "view_name": {"type": "string"},
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_view_dependencies",
            description=(
                "Return the authoritative list of tables and views that a D365 DMF view depends on, "
                "using sys.sql_expression_dependencies. More accurate than get_view_source_tables — "
                "correctly resolves CTEs, subqueries, and multi-level view references. "
                "Returns base_tables, views, and other dependencies separately."
            ),
            inputSchema={
                "type": "object",
                "required": ["view_name"],
                "properties": {
                    "view_name": {
                        "type": "string",
                        "description": "DMF view name in UPPERCASE, e.g. 'HCMWORKERENTITY', 'CUSTINVOICEJOURNALLINEENTITY'.",
                    },
                    "include_views": {
                        "type": "boolean",
                        "description": "Include dependent views in results (default: true). Set false to return base tables only.",
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_table_schema",
            description=(
                "Return the column schema (names, types, nullability) for any D365 AxDB table or view. "
                "Works for tables and views across all D365 modules."
            ),
            inputSchema={
                "type": "object",
                "required": ["object_name"],
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": (
                            "Table or view name in UPPERCASE, e.g. 'HCMWORKER' (HR), "
                            "'LEDGERJOURNALTABLE' (Finance), 'INVENTTABLE' (SCM), 'CUSTTABLE' (AR)."
                        ),
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_entity_columns",
            description=(
                "Return columns for a D365 DMF entity view, annotated with which source "
                "AxDB tables each column originates from."
            ),
            inputSchema={
                "type": "object",
                "required": ["view_name"],
                "properties": {
                    "view_name": {"type": "string"},
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_custom_fields",
            description=(
                "Return custom / extension fields (GNS* prefix or _CUSTOM suffix) for a named D365 AxDB table. "
                "Use this to discover implementation-specific extensions to the D365 data model "
                "across any module (HR, Finance, SCM, etc.)."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name"],
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": (
                            "Table name in UPPERCASE, e.g. 'HCMWORKER' (HR), "
                            "'CUSTTABLE' (AR), 'INVENTTABLE' (SCM)."
                        ),
                    },
                    "instance": {"type": "string"},
                },
            },
        ),

        # ── Data inspection tools ─────────────────────────────────────────

        types.Tool(
            name="get_row_count",
            description=(
                "Return the row count for a D365 AxDB table or view. "
                "Supports an optional WHERE clause for conditional counts, e.g. "
                "count only active workers, rows for a specific legal entity, etc."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name"],
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Table or view name, e.g. 'HCMWORKER', 'CUSTTABLE', 'INVENTTABLE'.",
                    },
                    "where_clause": {
                        "type": "string",
                        "description": (
                            "Optional SQL WHERE clause without the WHERE keyword. "
                            "Examples: \"EMPLSTATUS = 1\" | \"DATAAREAID = 'GBSI'\" | "
                            "\"CREATEDDATETIME >= '2024-01-01'\""
                        ),
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_data_sample",
            description=(
                "Return a sample of rows from a D365 AxDB table or view. "
                "Useful for understanding data shape and content. "
                "Supports optional WHERE filter, column selection, and ORDER BY."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name"],
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Table or view name, e.g. 'HCMWORKER', 'INVENTTABLE'.",
                    },
                    "top": {
                        "type": "integer",
                        "description": "Number of rows to return (default 10, max 200).",
                    },
                    "where_clause": {
                        "type": "string",
                        "description": "Optional SQL WHERE clause without the WHERE keyword.",
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of column names to return. Default: all columns.",
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Optional ORDER BY expression, e.g. 'CREATEDDATETIME DESC'.",
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_distinct_values",
            description=(
                "Return distinct values for a column in a D365 AxDB table or view, "
                "with optional row counts per value. "
                "Essential for understanding status fields, type enums, and reference data — "
                "e.g. what EMPLSTATUS values exist, or which DATAAREAID values are populated."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name", "column_name"],
                "properties": {
                    "table_name": {"type": "string", "description": "Table or view name."},
                    "column_name": {
                        "type": "string",
                        "description": "Column to inspect, e.g. 'EMPLSTATUS', 'DATAAREAID', 'TYPE'.",
                    },
                    "limit": {"type": "integer", "description": "Max distinct values to return (default 100)."},
                    "where_clause": {"type": "string", "description": "Optional SQL WHERE clause to pre-filter."},
                    "include_counts": {
                        "type": "boolean",
                        "description": "Include row count per value (default true).",
                    },
                    "instance": {"type": "string"},
                },
            },
        ),

        # ── Extended schema tools ─────────────────────────────────────────

        types.Tool(
            name="get_column_count",
            description=(
                "Return the column count for a D365 AxDB table or view. "
                "Supports an optional name pattern filter — e.g. count only GNS custom columns, "
                "only date columns, only ID/FK columns. Also returns a breakdown by data type."
            ),
            inputSchema={
                "type": "object",
                "required": ["object_name"],
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "Table or view name, e.g. 'HCMPOSITION', 'INVENTTABLE'.",
                    },
                    "name_filter": {
                        "type": "string",
                        "description": (
                            "Optional SQL LIKE pattern on column name. "
                            "Examples: 'GNS%' (custom fields) | '%DATE%' | '%ID' | '%_CUSTOM'"
                        ),
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_table_indexes",
            description=(
                "Return all indexes defined on a D365 AxDB table, including primary keys, "
                "unique indexes, and non-unique indexes, with the columns they cover. "
                "Useful for understanding D365 surrogate keys, RECID indexes, and query performance."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name"],
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Table name, e.g. 'HCMWORKER', 'INVENTTRANS', 'SALESTABLE'.",
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_related_tables",
            description=(
                "Return foreign key relationships for a D365 AxDB table — "
                "both outbound (this table references others) and inbound (other tables reference this one). "
                "Use this to trace the D365 data model, find child/parent relationships, "
                "and understand which tables join to a given table."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name"],
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Table name, e.g. 'HCMWORKER', 'CUSTTABLE', 'INVENTTABLE'.",
                    },
                    "instance": {"type": "string"},
                },
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        match name:
            case "list_d365_instances":
                result = list_d365_instances()
            case "list_dmf_views":
                result = list_dmf_views(**arguments)
            case "list_tables":
                result = list_tables(**arguments)
            case "search_objects":
                result = search_objects(**arguments)
            case "search_by_column":
                result = search_by_column(**arguments)
            case "get_view_sql":
                result = get_view_sql(**arguments)
            case "get_view_source_tables":
                result = get_view_source_tables(**arguments)
            case "get_view_dependencies":
                result = get_view_dependencies(**arguments)
            case "get_table_schema":
                result = get_table_schema(**arguments)
            case "get_entity_columns":
                result = get_entity_columns(**arguments)
            case "get_custom_fields":
                result = get_custom_fields(**arguments)
            case "get_row_count":
                result = get_row_count(**arguments)
            case "get_data_sample":
                result = get_data_sample(**arguments)
            case "get_distinct_values":
                result = get_distinct_values(**arguments)
            case "get_column_count":
                result = get_column_count(**arguments)
            case "get_table_indexes":
                result = get_table_indexes(**arguments)
            case "get_related_tables":
                result = get_related_tables(**arguments)
            case _:
                result = {"error": f"Unknown tool: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as exc:
        log.exception("Tool %s failed", name)
        return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def _main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    import asyncio
    asyncio.run(_main())


if __name__ == "__main__":
    main()
