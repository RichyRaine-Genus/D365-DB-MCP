"""
D365 MCP Server — instance registry.

This server is agnostic across all D365 / F&O value streams:
  Human Resources, Finance, Supply Chain Management, Project Operations, etc.

On a Tier-1 DEV box all modules share a single AxDB database, so a single
'default' instance entry covers the whole application.  If your team runs
dedicated DEV VMs (e.g. separate Finance vs SCM boxes) add extra entries below
and point each at the appropriate server via environment variables.

Instance env-var naming convention:
  AXDB_<INSTANCE_KEY>_SERVER    (e.g. AXDB_FINANCE_SERVER)
  AXDB_<INSTANCE_KEY>_DATABASE  (e.g. AXDB_FINANCE_DATABASE)
  Falls back to AXDB_SERVER / AXDB_DATABASE for the 'default' instance.
"""

import os
from db_config import AXDB_SERVER, AXDB_DATABASE, AXDB_DRIVER

# ---------------------------------------------------------------------------
# Module-prefix catalogue — used by list_dmf_views when no prefix= is supplied.
# Add or remove prefixes to suit the value streams your team works with.
# ---------------------------------------------------------------------------
_ALL_PREFIXES: list[str] = [
    # Human Resources / Human Capital Management
    "HCM",      # Human Capital Management
    "DIR",      # Directory / Party / Global Address Book
    # Finance
    "LEDGER",   # General Ledger
    "CUST",     # Accounts Receivable / Customers
    "VEND",     # Accounts Payable / Vendors
    "TAX",      # Tax
    "BUDGET",   # Budgeting
    "BANK",     # Cash & Bank Management
    "ASSET",    # Fixed Assets
    "COST",     # Cost accounting
    # Supply Chain Management
    "INVENT",   # Inventory
    "PROD",     # Production
    "PURCH",    # Procurement & Sourcing
    "SALES",    # Sales & Marketing
    "WHS",      # Warehouse Management
    "TRANS",    # Transportation Management
    "REQUIS",   # Requisitions
    # Project Operations
    "PROJ",     # Project Management & Accounting
    # Cross-module / shared
    "OMOPER",   # Legal entity / Operating unit
    "SMMACTIVITY",  # CRM / Activities
    "RETAIL",   # Commerce / Retail
]

# Registry of D365 instances accessible from this machine.
# 'default' points at the AxDB configured in .env / env vars.
# Add further entries for teams with separate DEV machines per module.
INSTANCES: dict[str, dict] = {
    "default": {
        "label": "D365 AxDB (default)",
        "server": AXDB_SERVER,
        "database": AXDB_DATABASE,
        "driver": AXDB_DRIVER,
        "view_prefixes": _ALL_PREFIXES,
    },
    # Example: separate Finance DEV box.
    # Set AXDB_FINANCE_SERVER in .env to activate.
    # "finance": {
    #     "label": "D365 Finance & Operations",
    #     "server": os.environ.get("AXDB_FINANCE_SERVER", AXDB_SERVER),
    #     "database": os.environ.get("AXDB_FINANCE_DATABASE", AXDB_DATABASE),
    #     "driver": AXDB_DRIVER,
    #     "view_prefixes": ["LEDGER", "CUST", "VEND", "TAX", "BUDGET", "BANK", "ASSET"],
    # },
    # Example: separate SCM DEV box.
    # "scm": {
    #     "label": "D365 Supply Chain Management",
    #     "server": os.environ.get("AXDB_SCM_SERVER", AXDB_SERVER),
    #     "database": os.environ.get("AXDB_SCM_DATABASE", AXDB_DATABASE),
    #     "driver": AXDB_DRIVER,
    #     "view_prefixes": ["INVENT", "PROD", "PURCH", "SALES", "WHS", "TRANS"],
    # },
}

DEFAULT_INSTANCE = "default"


def get_instance(name: str | None = None) -> dict:
    """Return instance config by name, defaulting to 'default'."""
    key = (name or DEFAULT_INSTANCE).lower()
    if key not in INSTANCES:
        raise ValueError(
            f"Unknown D365 instance '{key}'. "
            f"Available: {list(INSTANCES.keys())}"
        )
    return INSTANCES[key]
