## Quick orientation — D365 AxDB MCP server

This repo provides a small Model Context Protocol (MCP) server that gives AI agents
read-only, stdio-based access to a local Dynamics 365 / F&O AxDB (Tier-1 DEV) via ODBC.
It is **agnostic across all D365 value streams** — HR, Finance, Supply Chain, Projects, etc.
Keep instructions short and use the concrete project file names below when coding.

### Big picture (what to read first)
- `mcp_server/server.py` — MCP tool registration and dispatch (entry point).
- `mcp_server/tools/discovery.py` and `mcp_server/tools/schema.py` — the 9 core tools
  (list_d365_instances, list_dmf_views, list_tables, search_objects,
  get_view_sql, get_view_source_tables, get_table_schema, get_entity_columns,
  get_custom_fields).
- `mcp_server/config.py` — instance registry; `get_instance()` is the canonical way
  to resolve an instance name. The `_ALL_PREFIXES` list covers module prefixes for
  all D365 value streams.
- `db_config.py` — env loading and `get_axdb_conn()`; shows how connections are built.

### Transport and runtime
- Protocol: MCP over stdio — the server is run as a subprocess (see `main()` in
  `mcp_server/server.py`). Do not convert to an HTTP server without explicit reason.
- All database connections use Windows Authentication (Trusted_Connection) and
  `ApplicationIntent=ReadOnly` (see `db_config.py`). Tests and tools assume domain
  access to the DEV machine.

### Conventions and important patterns
- Uppercase D365 object names: all table/view names are UPPERCASE in AxDB (e.g.
  `HCMWORKER`, `CUSTTABLE`, `INVENTTABLE`, `SALESORDERHEADERENTITY`).
  Search and SQL queries in the code call `.upper()`.
- Connection-per-call pattern: tools open/close a pyodbc connection for each call
  (helper `_conn()` in each tool module). Expect ~50–200ms overhead — acceptable
  for conversational agent usage but not for bulk loops.
- Tool registration pattern: to add a tool update three places:
  1) implement function in `mcp_server/tools/*`, 2) import it in `server.py`,
  3) add a `types.Tool(...)` in `list_tools()` and a `case "name": result = fn(**arguments)`
  in `call_tool()`.

### Known heuristics & gotchas to mention when editing code
- `get_view_source_tables` uses a regex heuristic to extract FROM/JOIN targets and
  filters names shorter than 8 chars; it may return false positives for CTEs
  and inline views. If accuracy is required, prefer `sys.sql_expression_dependencies`.
- `search_objects` interpolates `keyword` into a LIKE expression; inputs are
  internal but avoid exposing this directly to untrusted inputs.
- The default instance is `default` (see `DEFAULT_INSTANCE` in `mcp_server/config.py`).
  Additional instances (e.g. `finance`, `scm`) can be uncommented in `config.py` for
  teams with separate DEV VMs per value stream.

### How to run locally (developer workflow)
- Recommended: run the installer once (PowerShell) — `Install-D365MCP.ps1` sets up
  `.venv` and writes a personal `.env` (gitignored). The MCP VS Code integration
  reads `.env` via `.vscode/mcp.json`.

Example quick checks to run in PowerShell (repo root):
```powershell
# Activate venv then run the connection test
.\.venv\Scripts\Activate.ps1; .\.venv\Scripts\python.exe tools\connection_test.py

# Run the MCP server directly for manual testing
.\.venv\Scripts\python.exe -m mcp_server.server
```

### Useful examples for the agent to reference
- Show SQL for a DMF view (HR): `get_view_sql(view_name='HCMWORKERENTITY')`
- Show SQL for a DMF view (Finance): `get_view_sql(view_name='CUSTINVOICEJOURNALENTITY')`
- Show SQL for a DMF view (SCM): `get_view_sql(view_name='SALESORDERHEADERENTITY')`
- Find source tables: `get_view_source_tables(view_name='HCMPOSITIONDETAILENTITY')` —
  document the regex limitations in the returned explanation.
- Inspect custom fields: `get_custom_fields(table_name='CUSTTABLE')` — looks for
  `GNS*` prefix or `_CUSTOM` suffix.
- Search across modules: `search_objects(keyword='WORKER')` or `search_objects(keyword='INVOICE')`

### When changing DB access or adding instances
- Add/modify `INSTANCES` in `mcp_server/config.py`. Use environment variables
  for server/database names (see `db_config.py` for naming: `AXDB_SERVER`,
  `AXDB_DATABASE`, `AXDB_DRIVER`). Update `.env.example` when adding new vars.
- To add a new value-stream instance (e.g. `finance`): set env var
  `AXDB_FINANCE_SERVER` and uncomment the `finance` block in `config.py`.

### Priorities for automated changes suggested to the repo
1. Add unit tests for `get_view_source_tables` (regex) — small, deterministic inputs.
2. Parameterize `search_objects` to avoid inline interpolation.
3. Optional: add an in-memory connection pool wrapper for heavy batch operations.

If you need clarification or more examples (prompts / expected JSON outputs), ask
which tool or function you want the agent to extend and I will provide a short
example input/output pair to embed in the docs.
