# D365 AxDB MCP Server — Team Onboarding Guide

> **Goal:** Connect GitHub Copilot (Agent mode) in *any* project to your local AxDB,
> so you can query D365 tables and entities without leaving your IDE.
> Works in both **VS Code** and **Visual Studio 2022 (Pro/Enterprise)**.

---

## How it works

The MCP server lives in its own repo (`D365-DB-MCP`).  
Your IDE points to it from **any project folder** via a single config file.  
You clone the server repo once, run the installer once, then reference it from wherever you work.

```
Your project folder (e.g. X:\Dev\MyProject)
  ├─ .vscode\mcp.json        ← VS Code users
  └─ .vs\mcp.json            ← Visual Studio users (next to your .sln)

D365-DB-MCP clone (e.g. C:\Dev\d365-mcp-server)
  ├─ .venv\              ← Python environment (created by installer)
  ├─ .env                ← your machine name (created by installer, gitignored)
  └─ mcp_server\server.py
```

---

## Step 1 — Prerequisites

Make sure these are installed on your **Tier 1 DEV machine**:

| # | Requirement | Check / Download |
|---|---|---|
| 1 | **Python 3.11+** | `python --version` — [python.org](https://www.python.org/downloads/) (tick *Add to PATH*) |
| 2 | **ODBC Driver 17 for SQL Server (64-bit)** | [aka.ms/odbc17](https://aka.ms/odbc17) |
| 3 | **GitHub Copilot** in your IDE | VS Code: extension `GitHub.copilot-chat` · Visual Studio: included via subscription |
| 4 | **Git** | `git --version` |

> **Tier 1 DEV only.** AxDB is only reachable locally on your `GNSPLC-DEV-###` box.
> If you're on a different machine, RDP to your DEV box first.

---

## Step 2 — Clone and install the server (one-time, all IDEs)

Pick a stable folder for shared tools — e.g. `C:\Dev\` or your Desktop.

```powershell
# Clone the repo
git clone https://github.com/RichyRaine-Genus/D365-DB-MCP.git
cd D365-DB-MCP

# Run the one-shot installer
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\Install-D365MCP.ps1
```

The installer will:
1. Check Python and ODBC Driver 17 are present
2. Create a `.venv` inside the repo and install all dependencies
3. Ask for your `AXDB_SERVER` name (defaults to your current machine name — just press Enter)
4. Write your personal `.env` file (gitignored — never pushed)
5. Run a live connection test to confirm everything works

✅ **You never need to open this folder in your IDE.** It just runs in the background.

---

## Step 3a — Wire your project (VS Code)

In **your own project folder**, create (or add to) `.vscode/mcp.json`:

```jsonc
{
  "servers": {
    "d365-axdb": {
      "type": "stdio",
      "command": "C:\\Dev\\D365-DB-MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "C:\\Dev\\D365-DB-MCP",
      "envFile": "C:\\Dev\\D365-DB-MCP\\.env"
    }
  }
}
```

> ⚠️ Replace `C:\\Dev\\D365-DB-MCP` with your actual clone path. Use double backslashes in JSON.

**Quick way to find your clone path:**
```powershell
cd D365-DB-MCP
(Get-Item .).FullName
```

---

## Step 3b — Wire your project (Visual Studio 2022)

> Requires **Visual Studio 2022 v17.13 or later** with the **GitHub Copilot** component.  
> Check: `Help → About Microsoft Visual Studio`  
> Update: `Help → Check for Updates`

Create **`.vs\mcp.json`** in your solution root (the folder containing your `.sln` file):

```jsonc
{
  "servers": {
    "d365-axdb": {
      "type": "stdio",
      "command": "C:\\Dev\\D365-DB-MCP\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "cwd": "C:\\Dev\\D365-DB-MCP",
      "env": {
        "AXDB_SERVER": "GNSPLC-DEV-###",
        "AXDB_DATABASE": "AxDB",
        "AXDB_DRIVER": "ODBC Driver 17 for SQL Server"
      }
    }
  }
}
```

> ⚠️ Replace `C:\\Dev\\D365-DB-MCP` with your actual clone path.  
> Replace `GNSPLC-DEV-###` with your machine name — run `$env:COMPUTERNAME` to find it.

> ℹ️ Visual Studio does **not** support `envFile` — environment variables must be inlined in the `env` block.  
> The `.vs\` folder is gitignored by default, so each developer maintains their own local copy with their own machine name. This is by design.

---

## Quick-reference: VS Code vs Visual Studio 2022

| | VS Code | Visual Studio 2022 |
|---|---|---|
| **Min version** | Any recent | 17.13+ |
| **Config file** | `.vscode\mcp.json` | `.vs\mcp.json` (next to `.sln`) |
| **`envFile` supported** | ✅ Yes | ❌ No — use `env` block instead |
| **Gitignored by default** | No (you choose) | Yes (`.vs\` is auto-ignored) |
| **Open chat** | `Ctrl+Alt+I` | `View → GitHub Copilot Chat` |
| **Switch to Agent mode** | Dropdown in chat input | Mode selector in chat panel |
| **Find tools** | Click 🔧 Tools button | Click **Add Tools** |

---

## Step 4 — Start querying

**VS Code:**
1. Open your project → `Ctrl+Alt+I` → switch to **Agent mode** → click **🔧 Tools**

**Visual Studio 2022:**
1. Open your solution → `View → GitHub Copilot Chat` → switch to **Agent mode** → click **Add Tools**

Confirm `d365-axdb` appears in the tool list, then try:

```
How many workers are in HCMWORKER?
```
```
Show me the schema for CUSTINVOICEJOURNALENTITY
```
```
What tables contain the column LEGALENTITYID?
```
```
List all DMF views with the LEDGER prefix
```

---

## Available Tools

| Tool | What it does |
|---|---|
| `list_d365_instances` | Show registered AxDB instances |
| `list_dmf_views` | List DMF export views, filter by module (`HCM`, `LEDGER`, `SALES`, etc.) |
| `list_tables` | List base tables by pattern (e.g. `INVENT%`) |
| `search_objects` | Find tables/views by keyword |
| `search_by_column` | Find all tables/views containing a specific column name |
| `get_view_sql` | Full SQL definition of a DMF view |
| `get_view_source_tables` | Base tables a view reads from (fast heuristic regex) |
| `get_view_dependencies` | Authoritative object dependencies via `sys.sql_expression_dependencies` — resolves CTEs and subqueries correctly |
| `get_table_schema` | Column names, types and nullability |
| `get_entity_columns` | DMF entity columns with their source tables |
| `get_custom_fields` | Genus custom fields (`GNS*` or `_CUSTOM`) on any table |
| `get_row_count` | Row count, with optional `WHERE` filter |
| `get_distinct_values` | Frequency distribution of values in a column |
| `get_data_sample` | `SELECT TOP n` with optional column list and filter |
| `get_column_count` | Column count with optional name pattern filter |
| `get_table_indexes` | All indexes on a table with columns and key type |
| `get_related_tables` | FK relationships in and out of a table |

---

## Troubleshooting

**Tools don't appear in Agent mode**
- VS Code: Reload window — `Ctrl+Shift+P` → `Developer: Reload Window`
- Visual Studio: Close and reopen the solution
- Check paths in your `mcp.json` — use `\\` not `\`
- VS Code: Check Output panel → select `MCP` from the dropdown for startup errors

**`[IM002] Data source name not found`**  
ODBC Driver 17 (64-bit) is not installed. Download from [aka.ms/odbc17](https://aka.ms/odbc17).

**`Login failed` or `Cannot open database`**  
- Confirm you're logged in with your **domain account** (not a local account)
- Confirm `AXDB_SERVER` matches your machine name: run `$env:COMPUTERNAME`
- Confirm D365 services are running:
  ```powershell
  Get-Service -DisplayName "Microsoft Dynamics*" | Select Name, Status
  ```

**Run the connection test manually at any time:**
```powershell
cd C:\Dev\D365-DB-MCP
.\.venv\Scripts\python.exe tools\connection_test.py
```

---

## Keeping the server up to date

When the repo is updated with new tools, a simple pull is all you need — no reinstall:

```powershell
cd C:\Dev\D365-DB-MCP
git pull
```

If `requirements.txt` changes (rare), run inside the venv:
```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```