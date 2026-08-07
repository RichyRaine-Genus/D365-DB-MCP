# D365 AxDB — MCP Server

Gives GitHub Copilot (Agent mode) and other MCP clients live read-only access
to a D365 / F&O AxDB on your local Tier 1 DEV machine.

Works across **all D365 value streams** — Human Resources, Finance, Supply Chain
Management, Project Operations, Commerce, and more.  Every team member connects
to their own Tier 1 DEV box; the server is agnostic about which modules are in use.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Windows domain account** | Must have read access to your `GNSPLC-DEV-###` machine |
| **Python 3.11+** | [python.org/downloads](https://www.python.org/downloads/) — tick "Add to PATH" |
| **ODBC Driver 17 for SQL Server** | [aka.ms/odbc17](https://aka.ms/odbc17) — 64-bit version |
| **VS Code** with GitHub Copilot | Extension ID: `GitHub.copilot-chat` |
| **Visual Studio 2022 v17.13+** | Alternative to VS Code — GitHub Copilot component required |
| **Git clone of this repo** | `git clone <repo-url>` |

> **Tier 1 DEV only.**
> The AxDB is only reachable from your local `GNSPLC-DEV-###` machine.
> Tier 2 / UAT / Production are Azure-hosted and not directly accessible.
> If you are on a different machine you will need to RDP to your DEV box first.

---

## Quick Install (recommended)

Open PowerShell **in the repo root** and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\Install-D365MCP.ps1
```

The script will:
1. Check Python version and ODBC Driver 17
2. Create `.venv` and install all dependencies
3. Prompt you for your `AXDB_SERVER` name (defaults to `$env:COMPUTERNAME`)
4. Write your personal `.env` file (never committed to Git)
5. Run a live connection test — confirms AxDB connectivity and detects D365 database
6. Confirm `.vscode/mcp.json` is present

Then open the repo in VS Code → Copilot Chat → **Agent mode**.

---

## Manual Install

If you prefer to set up manually:

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env (copy example and fill in your machine name)
Copy-Item .env.example .env
notepad .env
```

Edit `.env`:

```dotenv
AXDB_SERVER=GNSPLC-DEV-265    # ← replace with YOUR machine name
AXDB_DATABASE=AxDB
AXDB_DRIVER=ODBC Driver 17 for SQL Server
```

Your machine name is shown in **Settings → System → About → Device name**,
or run `$env:COMPUTERNAME` in PowerShell.

---

## Verifying the Connection

```powershell
.\.venv\Scripts\python.exe tools\connection_test.py
```

Expected output:
```
Connecting to GNSPLC-DEV-265 / AxDB
SQL Server version: Microsoft SQL Server 2019 ...
Total tables in AxDB: 22237
Looks like D365 AxDB: Yes
OK
```

If it fails, see [Troubleshooting](#troubleshooting) below.

---

## How Your IDE Loads the Config

### VS Code
`.vscode/mcp.json` uses the `envFile` key pointing to `${workspaceFolder}/.env`.
VS Code loads it automatically before starting the MCP server — no extra steps needed.

### Visual Studio 2022 (v17.13+)
Create `.vs\mcp.json` next to your `.sln` file. Visual Studio does **not** support `envFile`,
so the three variables (`AXDB_SERVER`, `AXDB_DATABASE`, `AXDB_DRIVER`) must be inlined
in an `env` block. The `.vs\` folder is gitignored by default — each developer keeps
their own local copy with their own machine name.

See [ONBOARDING.md](ONBOARDING.md) for complete config snippets for both IDEs.

You do **not** need system environment variables or shell profile changes in either case.

---

## Available Tools

| Tool | Description |
|---|---|
| `list_d365_instances` | List registered AxDB instances and their configured module prefixes |
| `list_dmf_views` | List DMF entity export views — filter by module prefix (`HCM`, `LEDGER`, `INVENT`, `SALES`, etc.) |
| `list_tables` | List base tables matching a SQL `LIKE` pattern (e.g. `INVENT%`, `%CUSTOMER%`) |
| `search_objects` | Search tables and views by keyword across all modules |
| `search_by_column` | Find all tables and views that contain a specific column name |
| `get_view_sql` | Return the full SQL definition of a DMF view |
| `get_view_source_tables` | Parse a view's SQL and return base tables (fast heuristic regex) |
| `get_view_dependencies` | Authoritative object dependencies via `sys.sql_expression_dependencies` — correctly resolves CTEs, subqueries and nested views |
| `get_table_schema` | Return column names, types, and nullability for a table or view |
| `get_entity_columns` | Return DMF entity columns annotated with their source AxDB tables |
| `get_custom_fields` | Return Genus-added custom fields (`GNS*` prefix or `_CUSTOM` suffix) |
| `get_row_count` | Return row count for a table, with optional `WHERE` clause filter |
| `get_distinct_values` | Return frequency distribution of values in a column |
| `get_data_sample` | Return `SELECT TOP n` rows with optional column list and filter |
| `get_column_count` | Return column count with optional name pattern filter |
| `get_table_indexes` | Return all indexes on a table with columns and key type |
| `get_related_tables` | Return FK relationships in and out of a table |
| `get_security_role` | Return a D365 security role and its core metadata |
| `get_security_duty` | Return a D365 security duty and its metadata |
| `get_security_privilege` | Return a D365 security privilege and its metadata |
| `get_role_security_graph` | Return the duties, direct privileges, inherited privileges, and effective graph for a role |
| `get_role_permission_summary` | Return a human-readable summary of a role's effective permissions and counts |

### Example prompts

**HR / Human Capital Management**
```
List all HCM tables in the default instance
```
```
Show me the SQL for HCMWORKERENTITY
```
```
What base tables does HCMPOSITIONDETAILENTITY join?
```

**Finance**
```
Search for tables related to LEDGER
```
```
Get the schema for CUSTINVOICEJOURNALENTITY
```
```
What columns does VENDTABLE have?
```

**Supply Chain Management**
```
List all views with the INVENT prefix
```
```
What base tables does SALESORDERHEADERENTITY read from?
```
```
Get the schema for INVENTTABLE
```

**Cross-module / Discovery**
```
Search for all tables containing the word WORKER
```
```
What custom fields have been added to CUSTTABLE?
```
```
List all available D365 instances
```
```
What tables contain the column LEGALENTITYID?
```
```
How many rows are in CUSTTABLE?
```
```
Show me a sample of 10 rows from INVENTTABLE
```

**Security investigations**
```
Give me a permission summary for GNSHRHSAuditAdministratorRole
```
```
Show me the security graph for GNSHRHSAuditAdministratorRole
```
```
Tell me about the security duty GNSHRHSAuditAdministratorDuty
```
```
Describe the privilege GNSHRHSAuditCompliancePriv
```

---

## Troubleshooting

### `[IM002] Data source name not found`
ODBC Driver 17 is not installed, or only the 32-bit version is present.
Download the **64-bit** installer from [aka.ms/odbc17](https://aka.ms/odbc17).

### `Login failed` / `Cannot open database`
- Confirm `AXDB_SERVER` in `.env` matches your actual machine name (`$env:COMPUTERNAME`)
- Confirm you are logged in with your domain account (not a local account)
- Confirm the `Dynamics365` services are running on your DEV box:
  `Get-Service -DisplayName "Microsoft Dynamics*" | Select Name, Status`

### `ModuleNotFoundError: No module named 'mcp_server'`
The venv is not activated or dependencies are not installed.
Re-run the installer script or `pip install -r requirements.txt` inside the activated venv.

### MCP tools not appearing in VS Code
- Check that `.vscode/mcp.json` exists in the repo root
- Reload the VS Code window (`Ctrl+Shift+P` → `Developer: Reload Window`)
- Open Output panel → select `MCP` from the dropdown — look for startup errors
- Confirm `.env` exists and contains a valid `AXDB_SERVER` value

### MCP tools not appearing in Visual Studio 2022
- Confirm VS 2022 is version **17.13 or later** (`Help → About`)
- Confirm `.vs\mcp.json` exists next to your `.sln` file
- Confirm `AXDB_SERVER` in the `env` block matches your machine (`$env:COMPUTERNAME`)
- Close and reopen the solution to force a reload

### Tools appear but queries return errors
Run the connection test manually:
```powershell
.\.venv\Scripts\python.exe tools\connection_test.py
```
This isolates whether the issue is the MCP server or the database connection.

---

## Architecture Note

The server runs in **stdio mode** — your IDE spawns it as a subprocess when you
open a Copilot Agent chat. It exits when the IDE closes. No port is opened.

All queries are **read-only** (the Windows Auth account has no write grants on AxDB).

For full setup instructions including Visual Studio 2022 config, see [ONBOARDING.md](ONBOARDING.md).
