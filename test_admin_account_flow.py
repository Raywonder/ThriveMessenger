"""Regression checks for the server-side pending-account data contract."""

import importlib.util
import os
import sqlite3
import tempfile
import unittest


SERVER_PATH = os.path.join(os.path.dirname(__file__), "srv", "server.py")


def load_server():
    spec = importlib.util.spec_from_file_location("thrive_server_test", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PendingAccountSchemaTests(unittest.TestCase):
    def test_schema_and_default_expiry_are_created(self):
        server = load_server()
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "thrive.db")
            previous_db = server.DB
            try:
                server.DB = database
                server.init_db()
                with sqlite3.connect(database) as connection:
                    columns = {row[1] for row in connection.execute("PRAGMA table_info(pending_accounts)")}
                    expiry = connection.execute(
                        "SELECT value FROM server_settings WHERE key='pending_account_expiry_days'"
                    ).fetchone()[0]
                self.assertTrue({"username", "email", "created_by", "expires_at"}.issubset(columns))
                self.assertEqual(expiry, "7")
            finally:
                server.DB = previous_db

    def test_invite_token_is_bound_to_the_recipient(self):
        server = load_server()
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "thrive.db")
            previous_db = server.DB
            try:
                server.DB = database
                server.init_db()
                token = server._create_invite_token("newperson", "new@example.test", "admin", expires_hours=1)
                with sqlite3.connect(database) as connection:
                    row = connection.execute(
                        "SELECT invited_user, invited_email, used FROM invite_tokens WHERE token=?", (token,)
                    ).fetchone()
                self.assertEqual(row, ("newperson", "new@example.test", 0))
            finally:
                server.DB = previous_db


if __name__ == "__main__":
    unittest.main()
