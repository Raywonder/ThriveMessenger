import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from srv import server


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig_db, self.orig_voice = server.DB, server.VOICE_DIR
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.VOICE_DIR = str(Path(self.tmp.name) / "voice")
        server.init_db()
        con = sqlite3.connect(server.DB)
        rows = [("alice", "bob", "one", "2026-09-26T23:30:00", "m1"), ("bob", "alice", "two", "2026-09-27T00:30:00", "m2"),
                ("alice", "carol", "not for bob", "2026-09-27T01:00:00", "m3"), ("Alice", "Bob", "three 🎉", "2026-09-27T02:00:00", "m4")]
        for frm, to, body, ts, uid in rows:
            con.execute("INSERT INTO direct_message_history(frm,to_user,frm_canonical,to_canonical,body,source,sensitivity,handled_by_bot,delivered,created_at,msg_uid) "
                        "VALUES(?,?,?,?,?,'thrive','normal',0,1,?,?)", (frm, to, frm, to, body, ts, uid))
        con.commit(); con.close()

    def tearDown(self):
        server.DB, server.VOICE_DIR = self.orig_db, self.orig_voice
        self.tmp.cleanup()

    def test_order_pairing_and_case(self):
        items, more = server._history_query("bob", "ALICE")
        self.assertEqual([i["msg"] for i in items], ["one", "two", "three 🎉"])
        self.assertFalse(more)
        self.assertTrue(all(i["time"].endswith("Z") for i in items))
        self.assertEqual(server._history_query("carol", "bob")[0], [])

    def test_paging_with_before(self):
        items, more = server._history_query("alice", "bob", limit=2)
        self.assertEqual([i["msg"] for i in items], ["two", "three 🎉"])
        self.assertTrue(more)
        older, more2 = server._history_query("alice", "bob", before_seq=items[0]["seq"], limit=2)
        self.assertEqual([i["msg"] for i in older], ["one"])
        self.assertFalse(more2)

    def test_deleted_messages_are_hidden(self):
        self.assertTrue(server._apply_direct_message_change("alice", "m1", False)[0])
        self.assertNotIn("one", [i["msg"] for i in server._history_query("alice", "bob")[0]])

    def test_days_follow_the_users_timezone(self):
        utc = {d["day"]: d["count"] for d in server._history_days("alice", "bob", 0)}
        self.assertEqual(utc, {"2026-09-26": 1, "2026-09-27": 2})
        central = {d["day"]: d["count"] for d in server._history_days("alice", "bob", -300)}
        self.assertEqual(central, {"2026-09-26": 3})
        day_items, _ = server._history_query("alice", "bob", day="2026-09-26", tz_offset_minutes=-300)
        self.assertEqual(len(day_items), 3)

    def test_voice_only_for_the_two_people(self):
        os.makedirs(server.VOICE_DIR)
        path = os.path.join(server.VOICE_DIR, "v1.mp3")
        open(path, "wb").write(b"ID3fake")
        server._record_direct_message_history("alice", "bob", "Voice message (0:05)", msg_uid="v1", attachment_path=path)
        items, _ = server._history_query("bob", "alice")
        self.assertEqual(items[-1]["voice"], {"duration": 5, "voicemail": False, "stored": True})
        self.assertTrue(server._voice_for_participant("bob", "v1"))
        self.assertIsNone(server._voice_for_participant("carol", "v1"))


if __name__ == "__main__":
    unittest.main()
