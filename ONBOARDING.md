# D365 AxDB MCP Server — Team Onboarding Guide

> **Goal:** Connect GitHub Copilot (Agent mode) in *any* VS Code project to your local AxDB,
> so you can query D365 tables and entities without leaving your IDE.

---

## How it works

The MCP server lives in its own repo (`D365-DB-MCP`).  
VS Code can point to it from **any other project folder** by adding a single config entry.  
You clone the server repo once, run the installer once, then reference it from wherever you work.

```
Your project folder (e.g. X:\Dev\MyProject)
  └─ .vscode\
       └─ mcp.json  ← tells VS Code where the server lives
                       (absolute path to your D365-DB-MCP clone)

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
| 3 | **VS Code** with **GitHub Copilot Chat** extension | Extension ID: `GitHub.copilot-chat` |
| 4 | **Git** | `git --version` |

> **Tier 1 DEV only.** AxDB is only reachable locally on your `GNSPLC-DEV-###` box.
> If you're on a different machine, RDP to your DEV box first.

---

## Step 2 — Clone and install the server (one-time)

Pick a folder where you keep shared tools — e.g. `C:\Dev\` or your Desktop.

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

✅ You're done with the server itself. **You never need to open this folder in VS Code.**

---

## Step 3 — Wire your project to the server

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

> ⚠️ **Replace `C:\\Dev\\D365-DB-MCP`** with the actual path where you cloned the repo.
> Use double backslashes (`\\`) in JSON.

**Quick way to find your clone path:**
```powershell
# Run this inside the D365-DB-MCP folder
(Get-Item .).FullName
```

---

## Step 4 — Use it in VS Code

1. Open your project folder in VS Code
2. Open Copilot Chat: `Ctrl+Alt+I`
3. Switch to **Agent mode** (dropdown next to the chat input)
4. Click the **🔧 Tools** button — you should see the `d365-axdb` tools listed

If the tools appear, you're connected. Try:

```
How many workers are in HCMWORKER?
```
```
Show me the schema for CUSTINVOICEJOURNALENTITY
```
```
What tables contain the column LEGALENTITYID?
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
| `get_view_source_tables` | Base tables a view reads from |
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
- Reload VS Code: `Ctrl+Shift+P` → `Developer: Reload Window`
- Check Output panel → select `MCP` from the dropdown for startup errors
- Confirm the paths in your `mcp.json` are correct and use `\\` not `\`

**`[IM002] Data source name not found`**  
ODBC Driver 17 (64-bit) is not installed. Download from [aka.ms/odbc17](https://aka.ms/odbc17).

**`Login failed` or `Cannot open database`**  
- Confirm you're logged in with your **domain account** (not a local account)
- Confirm `AXDB_SERVER` in the `.env` file matches your machine: run `$env:COMPUTERNAME`
- Confirm D365 services are running: `Get-Service -DisplayName "Microsoft Dynamics*" | Select Name, Status`

**Run the connection test manually at any time:**
```powershell
cd C:\Dev\D365-DB-MCP
.\.venv\Scripts\python.exe tools\connection_test.py
```

---

## Keeping the server up to date

When the repo is updated with new tools, pull and you're done — no reinstall needed:

```powershell
cd C:\Dev\D365-DB-MCP
git pull
```

If `requirements.txt` changes (rare), re-run `pip install -r requirements.txt` inside the venv.
