import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from srv import server


class BotDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        server._unreachable_notified.clear()

    def tearDown(self):
        server.DB = self.orig
        self.tmp.cleanup()

    def test_unreachable_notice_is_said_once(self):
        self.assertTrue(server._first_unreachable_notice("dom", "Adam"))
        self.assertFalse(server._first_unreachable_notice("dom", "adam"))
        self.assertTrue(server._first_unreachable_notice("other", "Adam"))
        server._clear_unreachable_notices("ADAM")
        self.assertTrue(server._first_unreachable_notice("dom", "Adam"))

    def test_queued_messages_delivered_in_order_when_bot_signs_in(self):
        for i, uid in enumerate(("q1", "q2", "q3")):
            server._record_direct_message_history("dom", "Adam", f"message {i}", msg_uid=uid)
        con = sqlite3.connect(server.DB)
        for uid in ("q1", "q2", "q3"):
            con.execute("INSERT INTO pending_bot_messages(msg_uid,to_user,created_at) VALUES(?,?,?)", (uid, "Adam", "x"))
        con.commit(); con.close()
        server._apply_direct_message_change("dom", "q2", False)  # deleted before delivery: not sent
        sent = []
        with mock.patch.object(server, "_send_json_line", lambda sock, p: sent.append(p)):
            n = server._deliver_pending_bot_messages(object(), "adam")
        self.assertEqual(n, 2)
        self.assertEqual([p["msg"] for p in sent], ["message 0", "message 2"])
        self.assertTrue(all(p["from"] == "dom" and p.get("delayed") for p in sent))
        con = sqlite3.connect(server.DB)
        self.assertEqual(con.execute("select count(*) from pending_bot_messages").fetchone()[0], 0)
        con.close()

    def test_no_canned_acknowledgement_left_in_reply_path(self):
        src = open(server.__file__, encoding="utf-8").read()
        body = src[src.index("def _run_bot_reply("):src.index("original_reply = str(reply")]
        self.assertNotIn("_natural_no_model_reply", body)
        self.assertNotIn("I have it in context", body)


if __name__ == "__main__":
    unittest.main()
