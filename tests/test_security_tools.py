import unittest
from unittest.mock import patch

from mcp_server.tools import security


class FakeCursor:
    def __init__(self):
        self._results = []
        self._current = None
        self._count_calls = 0

    def execute(self, sql, *params):
        sql_upper = sql.upper()
        if "FROM SECURITYROLEDUTYEXPLODEDGRAPH" in sql_upper:
            self._results = [(4285, 123)]
        elif "FROM SECURITYROLEPRIVILEGEEXPLODEDGRAPH" in sql_upper:
            self._results = [(27019, 1001), (27020, 1002), (27021, 1003)]
        elif "FROM SECURITYROLEDUTYPRIVILEGEEXPLODEDGRAPH" in sql_upper:
            self._results = []
        elif "FROM SECURITYROLE" in sql_upper:
            self._results = [(754, "GNS HR - HS Audit Administrator", "GNSHRHSAUDITADMINISTRATORROLE", 1, True)]
        elif "FROM SECURITYPRIVILEGE WHERE RECID =" in sql_upper:
            lookup_map = {
                27019: ("GNSHRHSAuditCompliancePriv",),
                27020: ("GNSHRHSAuditDocumentPackPriv",),
                27021: ("GNSHRHSAuditParametersPriv",),
            }
            self._results = [lookup_map.get(params[0], ("UnknownPriv",))]
        elif "FROM SECURITYRESOURCEPRIVILEGEPERMISSIONS" in sql_upper and "COUNT(*)" in sql_upper:
            self._count_calls += 1
            if self._count_calls == 1:
                self._results = [(96,)]
            else:
                self._results = [(0,)]
        else:
            self._results = []
        return self

    def fetchone(self):
        if not self._results:
            return None
        return self._results[0]

    def fetchall(self):
        results = self._results
        self._results = []
        return results


class FakeConnection:
    def cursor(self):
        return FakeCursor()

    def close(self):
        return None


class SecurityToolTests(unittest.TestCase):
    def test_role_permission_summary_counts_effective_permission_rows(self):
        with patch.object(security, "_conn", return_value=FakeConnection()):
            result = security.get_role_permission_summary("GNSHRHSAuditAdministratorRole")

        self.assertTrue(result["found"])
        self.assertEqual(result["effective_permission_count"], 96)
        self.assertEqual(result["direct_privilege_count"], 3)
        self.assertEqual(result["duty_count"], 1)


if __name__ == "__main__":
    unittest.main()
