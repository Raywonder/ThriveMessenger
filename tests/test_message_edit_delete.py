import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from srv import server


class MessageEditDeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        server.DB = str(Path(self.temp_dir.name) / "server.db")
        server.init_db()
        server._record_direct_message_history("alice", "bob", "hello bob", delivered=True, msg_uid="m1")
        self.admins = mock.patch.object(server, "get_admins", return_value={"root_admin"})
        self.admins.start()

    def tearDown(self):
        self.admins.stop()
        server.DB = self.original_db
        self.temp_dir.cleanup()

    def _row(self):
        con = sqlite3.connect(server.DB)
        try:
            return con.execute("SELECT body, edited_by, deleted_at, deleted_by FROM direct_message_history WHERE msg_uid='m1'").fetchone()
        finally:
            con.close()

    def test_sender_can_edit_case_insensitively(self):
        ok, reason, row = server._apply_direct_message_change("Alice", "m1", True, "hello again")
        self.assertTrue(ok, reason)
        self.assertEqual(row, ("alice", "bob"))
        self.assertEqual(self._row()[:2], ("hello again", "Alice"))

    def test_recipient_cannot_edit_or_delete(self):
        ok, reason, _ = server._apply_direct_message_change("bob", "m1", True, "forged")
        self.assertFalse(ok)
        self.assertIn("Only the person who sent", reason)
        ok, _, _ = server._apply_direct_message_change("bob", "m1", False)
        self.assertFalse(ok)
        self.assertEqual(self._row()[0], "hello bob")

    def test_admin_can_edit_and_delete(self):
        self.assertTrue(server._apply_direct_message_change("root_admin", "m1", True, "moderated")[0])
        ok, _, row = server._apply_direct_message_change("root_admin", "m1", False)
        self.assertTrue(ok)
        body, _, deleted_at, deleted_by = self._row()
        self.assertEqual((body, deleted_by), ("", "root_admin"))
        self.assertTrue(deleted_at)

    def test_deleted_or_unknown_messages_are_rejected(self):
        self.assertTrue(server._apply_direct_message_change("alice", "m1", False)[0])
        self.assertFalse(server._apply_direct_message_change("alice", "m1", True, "back")[0])
        self.assertFalse(server._apply_direct_message_change("alice", "nope", False)[0])
        self.assertFalse(server._apply_direct_message_change("alice", "", False)[0])

    def test_empty_edit_rejected(self):
        self.assertFalse(server._apply_direct_message_change("alice", "m1", True, "   ")[0])


if __name__ == "__main__":
    unittest.main()
