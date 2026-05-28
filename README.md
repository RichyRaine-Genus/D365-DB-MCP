# D365 HR AxDB — MCP Server

Gives GitHub Copilot (Agent mode) and other MCP clients live read-only access
to the D365 HR AxDB on your local Tier 1 DEV machine.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| **Windows domain account** | Must have read access to your `GNSPLC-DEV-###` machine |
| **Python 3.11+** | [python.org/downloads](https://www.python.org/downloads/) — tick "Add to PATH" |
| **ODBC Driver 17 for SQL Server** | [aka.ms/odbc17](https://aka.ms/odbc17) — 64-bit version |
| **VS Code** with GitHub Copilot | Extension ID: `GitHub.copilot-chat` |
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
5. Run a live connection test — confirms row count from `HCMWORKER`
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
Connected to GNSPLC-DEV-265 / AxDB
SQL Server version: Microsoft SQL Server 2019 ...
HCMWORKER row count: 1234
OK
```

If it fails, see [Troubleshooting](#troubleshooting) below.

---

## How VS Code Loads Your Config

`.vscode/mcp.json` contains an `envFile` key pointing to `${workspaceFolder}/.env`.
VS Code automatically loads this file before starting the MCP server process,
so your `AXDB_SERVER` value is picked up without any extra steps.

You do **not** need to set system environment variables or modify your shell profile.

---

## Available Tools

| Tool | Description |
|---|---|
| `list_d365_instances` | List registered AxDB instances (HR, Finance, SCM) |
| `list_dmf_views` | List DMF entity export views — optionally filter by prefix (`HCM`, `DIR`, etc.) |
| `list_tables` | List base tables matching a SQL `LIKE` pattern (e.g. `HCM%`) |
| `search_objects` | Search tables and views by keyword |
| `get_view_sql` | Return the full SQL definition of a DMF view |
| `get_view_source_tables` | Parse a view's SQL and return the base tables it reads from |
| `get_table_schema` | Return column names, types, and nullability for a table or view |
| `get_entity_columns` | Return DMF entity columns annotated with their source AxDB tables |
| `get_custom_fields` | Return Genus-added custom fields (`GNS*` prefix or `_CUSTOM` suffix) |

### Example prompts

```
List all HCM tables in the hr instance
```
```
Show me the SQL for HCMWORKERENTITY
```
```
What base tables does HCMPOSITIONDETAILENTITY join?
```
```
What custom fields has Genus added to HCMWORKER?
```
```
Get the schema for HCMEMPLOYMENT
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

### Tools appear but queries return errors
Run the connection test manually:
```powershell
.\.venv\Scripts\python.exe tools\connection_test.py
```
This isolates whether the issue is the MCP server or the database connection.

---

## Architecture Note

The server runs in **stdio mode** — VS Code spawns it as a subprocess when you
open a Copilot Agent chat. It exits when VS Code closes. No port is opened.

All queries are **read-only** (the Windows Auth account has no write grants on AxDB).
