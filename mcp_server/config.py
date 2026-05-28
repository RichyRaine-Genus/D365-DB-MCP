"""
D365 MCP Server — instance registry.

Genus operates TWO D365 instances:
  - hr      : D365 HR (Human Resources)
  - finance : D365 Finance & Operations (covers Finance, Operations, and Supply Chain)

Add the 'finance' server name once confirmed with the infrastructure team.
"""

from db_config import AXDB_SERVER, AXDB_DATABASE, AXDB_DRIVER

# Registry of D365 instances accessible from this machine.
# Each entry is passed to db_config-style connection string construction.
INSTANCES: dict[str, dict] = {
    "hr": {
        "label": "D365 HR",
        "server": AXDB_SERVER,
        "database": AXDB_DATABASE,
        "driver": AXDB_DRIVER,
        # Module prefix filters for DMF view discovery
        "view_prefixes": [
            "HCM",    # Human Capital Management
            "DIR",    # Directory / Party
            "OMOPER", # Legal entity / Operating unit
        ],
    },
    # Uncomment and complete when Finance & Operations server name is confirmed:
    # "finance": {
    #     "label": "D365 Finance & Operations",
    #     "server": "TBC",           # confirm with infrastructure team
    #     "database": "AxDB",
    #     "driver": AXDB_DRIVER,
    #     "view_prefixes": [
    #         "LEDGER", "CUST", "VEND", "TAX", "BUDGET",
    #         "INVENT", "PROD", "PURCH", "SALES", "WHS",
    #         "PROJ",
    #     ],
    # },
}

DEFAULT_INSTANCE = "hr"


def get_instance(name: str | None = None) -> dict:
    """Return instance config by name, defaulting to 'hr'."""
    key = (name or DEFAULT_INSTANCE).lower()
    if key not in INSTANCES:
        raise ValueError(
            f"Unknown D365 instance '{key}'. "
            f"Available: {list(INSTANCES.keys())}"
        )
    return INSTANCES[key]
