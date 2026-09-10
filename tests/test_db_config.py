import os
import unittest
from importlib import reload

import pytest

import db_config


_DOTENV_KEYS = [
    "AXDB_SERVER",
    "AXDB_DATABASE",
    "AXDB_DRIVER",
    "AXDB_AUTH_MODE",
    "AXDB_USERNAME",
    "AXDB_PASSWORD",
    "AXDB_DOTENV",
]


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


@pytest.fixture
def clean_axdb_env(monkeypatch):
    """Delete AXDB_* keys first so any values load_dotenv injects are cleaned up
    on teardown, and never let a test read the developer's real .env."""
    for key in _DOTENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield monkeypatch
    reload(db_config)


class TestDotenvLoading:
    def test_dotenv_value_used_when_env_unset(self, clean_axdb_env, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("AXDB_SERVER=DOTENV-HOST\n")
        clean_axdb_env.setenv("AXDB_DOTENV", str(env_file))

        reload(db_config)

        assert db_config.AXDB_SERVER == "DOTENV-HOST"

    def test_os_env_overrides_dotenv(self, clean_axdb_env, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("AXDB_SERVER=DOTENV-HOST\n")
        clean_axdb_env.setenv("AXDB_DOTENV", str(env_file))
        clean_axdb_env.setenv("AXDB_SERVER", "REAL-HOST")

        reload(db_config)

        assert db_config.AXDB_SERVER == "REAL-HOST"

    def test_missing_dotenv_falls_back_to_defaults(self, clean_axdb_env, tmp_path):
        # Point at a non-existent file so the loader short-circuits before it
        # can reach cwd or the repo root — guarantees no real .env is read.
        clean_axdb_env.setenv("AXDB_DOTENV", str(tmp_path / "does-not-exist.env"))

        reload(db_config)

        assert db_config.AXDB_SERVER == "GNSPLC-DEV-283"

    def test_explicit_dotenv_path_is_honored(self, clean_axdb_env, tmp_path):
        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir()
        (cwd_dir / ".env").write_text("AXDB_SERVER=CWD-HOST\n")
        clean_axdb_env.chdir(cwd_dir)

        explicit = tmp_path / "explicit.env"
        explicit.write_text("AXDB_SERVER=EXPLICIT-HOST\n")
        clean_axdb_env.setenv("AXDB_DOTENV", str(explicit))

        reload(db_config)

        assert db_config.AXDB_SERVER == "EXPLICIT-HOST"


if __name__ == "__main__":
    unittest.main()
