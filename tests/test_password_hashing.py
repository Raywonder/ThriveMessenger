import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from srv import server


class PasswordHashingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        server.DB = str(Path(self.temp_dir.name) / "server.db")
        server.init_db()

    def tearDown(self):
        server.DB = self.original_db
        self.temp_dir.cleanup()

    def _stored(self, user):
        con = sqlite3.connect(server.DB)
        try:
            return con.execute("SELECT password FROM users WHERE username=?", (user,)).fetchone()[0]
        finally:
            con.close()

    def test_argon2_is_available_to_the_server(self):
        self.assertIsNotNone(server._ph, "argon2-cffi must be importable by the server's Python")

    def test_hash_never_plain_and_verifies(self):
        h = server._hash_password("correct horse")
        self.assertTrue(h.startswith("$argon2"))
        self.assertNotIn("correct horse", h)
        self.assertTrue(server._verify_password_for_login(h, "correct horse"))
        self.assertFalse(server._verify_password_for_login(h, "wrong"))

    def test_pbkdf2_fallback_when_argon2_missing(self):
        with mock.patch.object(server, "_ph", None):
            h = server._hash_password("fallback pw")
            self.assertTrue(h.startswith("$pbkdf2-sha256$"))
            self.assertTrue(server._verify_password_for_login(h, "fallback pw"))
            self.assertFalse(server._verify_password_for_login(h, "nope"))
        # Once argon2 is back, PBKDF2 rows are upgraded on next login.
        self.assertTrue(server._password_needs_rehash(h))

    def test_handle_create_stores_hash(self):
        server.handle_create("carol", "carol-secret-1", "")
        stored = self._stored("carol")
        self.assertTrue(stored.startswith("$argon2"))
        self.assertTrue(server._verify_password_for_login(stored, "carol-secret-1"))

    def test_migration_hashes_plain_rows_and_keeps_logins(self):
        con = sqlite3.connect(server.DB)
        con.execute("INSERT INTO users(username,password,is_verified) VALUES('dave','plain-dave-pw',1)")
        con.execute("INSERT INTO users(username,password,is_verified) VALUES('erin',?,1)", (server._hash_password("erin-pw"),))
        con.commit(); con.close()
        self.assertEqual(server.migrate_plaintext_passwords(), 1)
        self.assertEqual(server.migrate_plaintext_passwords(), 0)  # idempotent
        dave = self._stored("dave")
        self.assertTrue(dave.startswith("$argon2"))
        self.assertTrue(server._verify_password_for_login(dave, "plain-dave-pw"))
        self.assertTrue(server._verify_password_for_login(self._stored("erin"), "erin-pw"))

    def test_legacy_plain_row_rehashed_on_login(self):
        con = sqlite3.connect(server.DB)
        con.execute("INSERT INTO users(username,password,is_verified) VALUES('frank','frank-pw',1)")
        con.commit()
        self.assertTrue(server._verify_password_for_login("frank-pw", "frank-pw"))
        self.assertTrue(server._rehash_password_if_needed(con, "frank", "frank-pw", "frank-pw"))
        con.close()
        stored = self._stored("frank")
        self.assertTrue(stored.startswith("$argon2"))
        self.assertTrue(server._verify_password_for_login(stored, "frank-pw"))

    def test_hash_string_is_not_accepted_as_password(self):
        h = server._hash_password("real-pw")
        self.assertFalse(server._verify_password_for_login(h, h))


if __name__ == "__main__":
    unittest.main()
