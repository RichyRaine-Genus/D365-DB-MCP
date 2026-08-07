"""
D365 security analysis helpers.

These helpers are designed around the Finance and Operations security model:
- Roles group duties and privileges for users
- Duties group related privileges for a business function
- Privileges grant access to specific entry points and operations
- Permissions are the effective access entries derived from the graph

The implementation uses AxDB tables such as SECURITYROLE, SECURITYDUTY,
SECURITYPRIVILEGE, SECURITYROLEDUTYEXPLODEDGRAPH,
SECURITYROLEPRIVILEGEEXPLODEDGRAPH and
SECURITYROLEDUTYPRIVILEGEEXPLODEDGRAPH.
"""

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


def get_security_role(role_name: str, instance: str | None = None) -> dict:
    """Return a role row and its basic metadata by name or AOT name."""
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        sql = """
            SELECT TOP 1 RECID, NAME, AOTNAME, RECVERSION, CANBEDELETEDFROMUI
            FROM SECURITYROLE
            WHERE UPPER(NAME) = ? OR UPPER(AOTNAME) = ?
            ORDER BY NAME
        """
        cur.execute(sql, role_name.upper(), role_name.upper())
        row = cur.fetchone()
        if not row:
            return {"role_name": role_name.upper(), "found": False, "role": None}

        return {
            "role_name": role_name.upper(),
            "found": True,
            "role": {
                "recid": row[0],
                "name": row[1],
                "aotname": row[2],
                "recv_version": row[3],
                "can_be_deleted_from_ui": bool(row[4]),
            },
        }
    finally:
        conn.close()


def get_security_duty(duty_name: str, instance: str | None = None) -> dict:
    """Return a duty row and its basic metadata by name or AOT name."""
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        sql = """
            SELECT TOP 1 RECID, NAME, DESCRIPTION, RECVERSION, IDENTIFIER
            FROM SECURITYDUTY
            WHERE UPPER(NAME) = ? OR UPPER(IDENTIFIER) = ?
            ORDER BY NAME
        """
        cur.execute(sql, duty_name.upper(), duty_name.upper())
        row = cur.fetchone()
        if not row:
            return {"duty_name": duty_name.upper(), "found": False, "duty": None}

        return {
            "duty_name": duty_name.upper(),
            "found": True,
            "duty": {
                "recid": row[0],
                "name": row[1],
                "description": row[2],
                "recv_version": row[3],
                "identifier": row[4],
            },
        }
    finally:
        conn.close()


def get_security_privilege(privilege_name: str, instance: str | None = None) -> dict:
    """Return a privilege row and its basic metadata by name or AOT name."""
    conn = _conn(instance)
    try:
        cur = conn.cursor()
        sql = """
            SELECT TOP 1 RECID, NAME, DESCRIPTION, RECVERSION, IDENTIFIER
            FROM SECURITYPRIVILEGE
            WHERE UPPER(NAME) = ? OR UPPER(IDENTIFIER) = ?
            ORDER BY NAME
        """
        cur.execute(sql, privilege_name.upper(), privilege_name.upper())
        row = cur.fetchone()
        if not row:
            return {"privilege_name": privilege_name.upper(), "found": False, "privilege": None}

        return {
            "privilege_name": privilege_name.upper(),
            "found": True,
            "privilege": {
                "recid": row[0],
                "name": row[1],
                "description": row[2],
                "recv_version": row[3],
                "identifier": row[4],
            },
        }
    finally:
        conn.close()


def get_role_security_graph(role_name: str, instance: str | None = None) -> dict:
    """
    Return the security graph for a role:
    - direct privileges assigned to the role
    - duties assigned to the role
    - privileges inherited through those duties
    - effective total permission count from the exploded graph
    """
    role = get_security_role(role_name, instance)
    if not role["found"]:
        return {"role_name": role_name.upper(), "found": False, "data": None}

    recid = role["role"]["recid"]

    conn = _conn(instance)
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT SECURITYDUTY, RECID
            FROM SECURITYROLEDUTYEXPLODEDGRAPH
            WHERE SECURITYROLE = ?
            ORDER BY SECURITYDUTY
            """,
            recid,
        )
        assigned_duties = [
            {"duty_recid": row[0], "graph_recid": row[1]}
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT SECURITYPRIVILEGE, RECID
            FROM SECURITYROLEPRIVILEGEEXPLODEDGRAPH
            WHERE SECURITYROLE = ?
            ORDER BY SECURITYPRIVILEGE
            """,
            recid,
        )
        assigned_privileges = [
            {"privilege_recid": row[0], "graph_recid": row[1]}
            for row in cur.fetchall()
        ]

        cur.execute(
            """
            SELECT SECURITYDUTYRECID, SECURITYPRIVILEGERECID
            FROM SECURITYROLEDUTYPRIVILEGEEXPLODEDGRAPH
            WHERE SECURITYROLERECID = ?
            ORDER BY SECURITYDUTYRECID, SECURITYPRIVILEGERECID
            """,
            recid,
        )
        duty_privilege_rows = [
            {"duty_recid": row[0], "privilege_recid": row[1]}
            for row in cur.fetchall()
        ]

        privilege_ids = [entry["privilege_recid"] for entry in assigned_privileges]
        privilege_ids.extend(entry["privilege_recid"] for entry in duty_privilege_rows)
        privilege_ids = list(dict.fromkeys(privilege_ids))

        effective_permission_count = 0
        seen_identifiers = set()
        for privilege_recid in privilege_ids:
            cur.execute(
                "SELECT TOP 1 IDENTIFIER FROM SECURITYPRIVILEGE WHERE RECID = ?",
                privilege_recid,
            )
            privilege_row = cur.fetchone()
            if not privilege_row:
                continue
            privilege_identifier = privilege_row[0]
            if privilege_identifier in seen_identifiers:
                continue
            seen_identifiers.add(privilege_identifier)
            cur.execute(
                """
                SELECT COUNT(*)
                FROM SECURITYRESOURCEPRIVILEGEPERMISSIONS
                WHERE PRIVILEGEIDENTIFIER = ?
                """,
                privilege_identifier,
            )
            effective_permission_count += cur.fetchone()[0]

        return {
            "role_name": role_name.upper(),
            "found": True,
            "role": role["role"],
            "assigned_duties": assigned_duties,
            "assigned_privileges": assigned_privileges,
            "duty_privilege_links": duty_privilege_rows,
            "effective_permission_count": effective_permission_count,
            "notes": [
                "In the D365 security model, roles aggregate duties and privileges.",
                "Duties group related privileges for a business area.",
                "Permissions are derived from the effective privilege graph."
            ],
        }
    finally:
        conn.close()


def get_role_permission_summary(role_name: str, instance: str | None = None) -> dict:
    """
    Provide a human-readable security summary for a role, including:
    - direct privileges on the role
    - duties on the role
    - privileges inherited through duties
    - effective permission count
    """
    role_graph = get_role_security_graph(role_name, instance)
    if not role_graph["found"]:
        return role_graph

    conn = _conn(instance)
    try:
        cur = conn.cursor()

        def lookup_name(table: str, recid: int | None) -> str | None:
            if recid is None:
                return None
            if table == "SECURITYDUTY":
                cur.execute("SELECT TOP 1 NAME, IDENTIFIER FROM SECURITYDUTY WHERE RECID = ?", recid)
            elif table == "SECURITYPRIVILEGE":
                cur.execute("SELECT TOP 1 NAME, IDENTIFIER FROM SECURITYPRIVILEGE WHERE RECID = ?", recid)
            else:
                cur.execute(f"SELECT TOP 1 NAME FROM {table} WHERE RECID = ?", recid)
            row = cur.fetchone()
            if not row:
                return None
            if len(row) >= 2:
                return row[1] or row[0]
            return row[0]

        duties = []
        for entry in role_graph["assigned_duties"]:
            duties.append({
                "duty_recid": entry["duty_recid"],
                "duty_name": lookup_name("SECURITYDUTY", entry["duty_recid"]),
            })

        direct_privileges = []
        for entry in role_graph["assigned_privileges"]:
            direct_privileges.append({
                "privilege_recid": entry["privilege_recid"],
                "privilege_name": lookup_name("SECURITYPRIVILEGE", entry["privilege_recid"]),
            })

        inherited_privileges = []
        for entry in role_graph["duty_privilege_links"]:
            inherited_privileges.append({
                "duty_recid": entry["duty_recid"],
                "privilege_recid": entry["privilege_recid"],
                "privilege_name": lookup_name("SECURITYPRIVILEGE", entry["privilege_recid"]),
            })

        return {
            "role_name": role_name.upper(),
            "found": True,
            "role": role_graph["role"],
            "duty_count": len(duties),
            "direct_privilege_count": len(direct_privileges),
            "inherited_privilege_count": len(inherited_privileges),
            "effective_permission_count": role_graph["effective_permission_count"],
            "duties": duties,
            "direct_privileges": direct_privileges,
            "inherited_privileges": inherited_privileges,
            "notes": [
                "This summary uses the exploded graph tables available in AxDB.",
                "Try querying the role, then inspect the duties and privileges that feed it."
            ],
        }
    finally:
        conn.close()
