import tempfile
import unittest
from pathlib import Path
from unittest import mock

from srv import rooms, server


class ReactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        server._record_direct_message_history("dom", "clawdia", "Ship it?", delivered=True, msg_uid="d1")

    def tearDown(self):
        server.DB = self.orig
        self.tmp.cleanup()

    def test_dm_reactions_only_for_people_in_the_conversation(self):
        ok, _, upd, who = server._react("clawdia", "dm", "d1", "\U0001F44D")
        self.assertTrue(ok)
        self.assertEqual({w.lower() for w in who}, {"dom", "clawdia"})
        self.assertEqual(upd["reactions"], [{"emoji": "\U0001F44D", "users": ["clawdia"]}])
        self.assertFalse(server._react("eve", "dm", "d1", "\U0001F44D")[0])
        self.assertFalse(server._react("dom", "dm", "d1", "hello")[0])  # not an emoji
        server._react("dom", "dm", "d1", "❤️")
        items, _ = server._history_query("dom", "clawdia")
        self.assertEqual([g["emoji"] for g in items[0]["reactions"]], ["\U0001F44D", "❤️"])
        ok, _, upd, _ = server._react("clawdia", "dm", "d1", "\U0001F44D", on=False)
        self.assertEqual(upd["reactions"], [{"emoji": "❤️", "users": ["dom"]}])

    def test_room_reactions_members_only_and_in_history(self):
        room = rooms.create_room(server.DB, "dom", "R")
        rooms.join_room(server.DB, room["room_id"], "sophia")
        msg = rooms.add_message(server.DB, room["room_id"], "dom", "hi")
        with mock.patch.object(server, "_room_members", lambda rid: ["dom", "sophia"]):
            self.assertTrue(server._react("sophia", "room", msg["message_id"], "\U0001F440", room_id=room["room_id"])[0])
            self.assertFalse(server._react("eve", "room", msg["message_id"], "\U0001F440", room_id=room["room_id"])[0])
        payload = server._room_open_payload(room["room_id"], "dom")
        self.assertEqual(payload["messages"][0]["reactions"], [{"emoji": "\U0001F440", "users": ["sophia"]}])


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        server._room_agent_replies.clear()
        self.room = rooms.create_room(server.DB, "dom", "Agent Access")
        for a in ("Clawdia", "Sophia"):
            rooms.add_member(server.DB, self.room["room_id"], "dom", a)

    def tearDown(self):
        server.DB = self.orig
        self.tmp.cleanup()

    def test_agents_answer_agents_only_when_mentioned_and_with_a_cooldown(self):
        started = []
        rid = self.room["room_id"]
        with mock.patch.object(server, "_is_virtual_bot", lambda u: u.lower() in ("clawdia", "sophia")), \
                mock.patch.object(server.threading, "Thread", lambda target, args, **k: mock.Mock(start=lambda: started.append(args[2]))):
            server._room_maybe_bot_replies(rid, "Clawdia", {"mentions": []})
            self.assertEqual(started, [])
            server._room_maybe_bot_replies(rid, "Clawdia", {"mentions": ["Sophia"]})
            self.assertEqual(started, ["Sophia"])
            server._room_maybe_bot_replies(rid, "Clawdia", {"mentions": ["Sophia"]})
            self.assertEqual(started, ["Sophia"])  # cool-down
            server._room_maybe_bot_replies(rid, "dom", {"mentions": ["Sophia"]})
            self.assertEqual(started, ["Sophia", "Sophia"])  # a person is never held back by the agent cool-down


if __name__ == "__main__":
    unittest.main()
