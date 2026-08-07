import os
import unittest
from importlib import reload

import db_config


class DbConfigTests(unittest.TestCase):
    def tearDown(self):
        for key in ["AXDB_AUTH_MODE", "AXDB_USERNAME", "AXDB_PASSWORD"]:
            os.environ.pop(key, None)
        reload(db_config)

    def test_sql_auth_connection_string_uses_uid_and_pwd(self):
        os.environ["AXDB_AUTH_MODE"] = "sql"
        os.environ["AXDB_USERNAME"] = "sa"
        os.environ["AXDB_PASSWORD"] = "secret"

        reload(db_config)
        conn_str = db_config.axdb_conn_str(
            server="GNSPLC-DEV-285",
            database="AxDB",
            driver="ODBC Driver 17 for SQL Server",
        )

        self.assertIn("UID=sa", conn_str)
        self.assertIn("PWD=secret", conn_str)
        self.assertNotIn("Trusted_Connection=yes", conn_str)


if __name__ == "__main__":
    unittest.main()
