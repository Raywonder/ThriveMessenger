import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from srv import server


class OfflineDmQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        server._unreachable_notified.clear()

    def tearDown(self):
        server.DB = self.orig
        self.tmp.cleanup()

    def test_queued_offline_dm_delivered_in_order_on_next_sign_in(self):
        for i, uid in enumerate(("o1", "o2", "o3")):
            server._record_direct_message_history("dom", "carol", f"offline message {i}", msg_uid=uid)
        con = sqlite3.connect(server.DB)
        for uid in ("o1", "o2", "o3"):
            con.execute("INSERT INTO pending_offline_messages(msg_uid,to_user,created_at) VALUES(?,?,?)", (uid, "carol", "x"))
        con.commit(); con.close()
        sent = []
        with mock.patch.object(server, "_send_json_line", lambda sock, p: sent.append(p)):
            n = server._deliver_pending_offline_messages(object(), "CAROL")
        self.assertEqual(n, 3)
        self.assertEqual([p["msg"] for p in sent], ["offline message 0", "offline message 1", "offline message 2"])
        self.assertTrue(all(p["from"] == "dom" and p.get("delayed") for p in sent))
        con = sqlite3.connect(server.DB)
        self.assertEqual(con.execute("select count(*) from pending_offline_messages").fetchone()[0], 0)
        con.close()

    def test_offline_table_created_by_init_db(self):
        con = sqlite3.connect(server.DB)
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_offline_messages'"
        ).fetchone()
        con.close()
        self.assertIsNotNone(row)


class BotErrorGuardTests(unittest.TestCase):
    def test_traceback_is_blocked(self):
        text, blocked, reason = server._user_facing_bot_output(
            "Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: boom"
        )
        self.assertTrue(blocked)
        self.assertEqual(reason, "error-like-reply")
        self.assertEqual(text, "")

    def test_usage_limit_text_is_blocked(self):
        text, blocked, reason = server._user_facing_bot_output("Sorry, usage limit hit for this account.")
        self.assertTrue(blocked)
        self.assertEqual(reason, "error-like-reply")

    def test_http_error_shape_is_blocked(self):
        text, blocked, reason = server._user_facing_bot_output("Request failed with HTTP 503 Service Unavailable")
        self.assertTrue(blocked)
        self.assertEqual(reason, "error-like-reply")

    def test_ordinary_reply_is_not_blocked(self):
        text, blocked, reason = server._user_facing_bot_output("Sure, I can help with that.")
        self.assertFalse(blocked)
        self.assertIsNone(reason)
        self.assertEqual(text, "Sure, I can help with that.")

    def test_blocked_reply_never_raises_without_app_health_installed(self):
        with mock.patch.object(server, "_APP_HEALTH_CLIENT", False):
            text, blocked, reason = server._user_facing_bot_output("codex stopped with an error")
            self.assertTrue(blocked)
            self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
