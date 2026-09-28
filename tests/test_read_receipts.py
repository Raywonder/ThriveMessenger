import tempfile
import unittest
from pathlib import Path
from unittest import mock

from srv import server


class ReadReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        server._record_direct_message_history("SystemMonitor", "tappedinfm", "hello Dom", delivered=True, msg_uid="r1")
        server._record_direct_message_history("SystemMonitor", "tappedinfm", "second", delivered=False, msg_uid="r2")

    def tearDown(self):
        server.DB = self.orig
        self.tmp.cleanup()

    def test_only_the_recipient_can_mark_read_and_sender_is_told(self):
        pushed = []
        with mock.patch.object(server, "_send_to_all_sessions", lambda users, p: pushed.append((set(users), p))):
            self.assertEqual(server._mark_messages_read("SystemMonitor", ["r1"]), 0)  # sender can't
            self.assertEqual(server._mark_messages_read("stranger", ["r1"]), 0)
            self.assertEqual(server._mark_messages_read("TappedInFM", ["r1", "nope"]), 1)
            self.assertEqual(server._mark_messages_read("tappedinfm", ["r1"]), 0)  # already read
        upd = [p for u, p in pushed if p["action"] == "msg_read_update"]
        self.assertEqual(len(upd), 1)
        self.assertEqual(upd[0]["ids"], ["r1"])
        self.assertEqual(upd[0]["by"], "TappedInFM")
        self.assertTrue(upd[0]["read_at"].endswith("Z"))

    def test_read_status_and_history_show_it(self):
        with mock.patch.object(server, "_send_to_all_sessions", lambda *a: None):
            server._mark_messages_read("tappedinfm", ["r1"])
        rows = {r["id"]: r for r in server._read_status("SystemMonitor", "tappedinfm")}
        self.assertTrue(rows["r1"]["read"] and rows["r1"]["read_at"])
        self.assertFalse(rows["r2"]["read"])
        self.assertFalse(rows["r2"]["delivered"])
        items = {i["id"]: i for i in server._history_query("tappedinfm", "SystemMonitor")[0]}
        self.assertTrue(items["r1"]["read_at"])
        self.assertIsNone(items["r2"]["read_at"])


if __name__ == "__main__":
    unittest.main()
