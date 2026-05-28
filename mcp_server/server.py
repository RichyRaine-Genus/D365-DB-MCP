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
)
from mcp_server.tools.schema import (
    get_view_sql,
    get_view_source_tables,
    get_table_schema,
    get_entity_columns,
    get_custom_fields,
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
                "These are the views that BYOD exports use as sources."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prefix": {"type": "string", "description": "Optional name prefix filter e.g. 'HCM', 'DIR'"},
                    "instance": {"type": "string", "description": "Instance name: 'hr' (default), 'finance', 'scm'"},
                    "limit": {"type": "integer", "description": "Max results (default 200)"},
                },
            },
        ),
        types.Tool(
            name="list_tables",
            description="List base tables in a D365 AxDB instance matching an optional SQL LIKE pattern.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "SQL LIKE pattern e.g. 'HCM%', '%WORKER%'"},
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
            name="get_view_sql",
            description="Return the full SQL definition of a named DMF view from D365 AxDB.",
            inputSchema={
                "type": "object",
                "required": ["view_name"],
                "properties": {
                    "view_name": {"type": "string", "description": "e.g. 'HCMWORKERENTITY'"},
                    "instance": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="get_view_source_tables",
            description=(
                "Parse a D365 DMF view's SQL and return the base AxDB tables it reads from, "
                "with their aliases."
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
            name="get_table_schema",
            description="Return the column schema (names, types, nullability) for a D365 AxDB table or view.",
            inputSchema={
                "type": "object",
                "required": ["object_name"],
                "properties": {
                    "object_name": {"type": "string", "description": "e.g. 'HCMWORKER'"},
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
                "Return custom fields (GNS* prefix or _CUSTOM suffix) for a named D365 AxDB table. "
                "Use this to discover Genus-added extensions to the D365 data model."
            ),
            inputSchema={
                "type": "object",
                "required": ["table_name"],
                "properties": {
                    "table_name": {"type": "string", "description": "e.g. 'HCMWORKER'"},
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
            case "get_view_sql":
                result = get_view_sql(**arguments)
            case "get_view_source_tables":
                result = get_view_source_tables(**arguments)
            case "get_table_schema":
                result = get_table_schema(**arguments)
            case "get_entity_columns":
                result = get_entity_columns(**arguments)
            case "get_custom_fields":
                result = get_custom_fields(**arguments)
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
