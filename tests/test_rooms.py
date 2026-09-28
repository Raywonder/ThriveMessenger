import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from srv import rooms, server


class FakeSock:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        for line in data.decode().splitlines():
            if line.strip():
                self.sent.append(json.loads(line))

    def last(self, action):
        return next((p for p in reversed(self.sent) if p.get("action") == action), None)


class RoomModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "r.db")
        rooms.init_schema(self.db)
        self.room = rooms.create_room(self.db, "dom", "Dom's Agents", topic="Agents and Dom")
        self.rid = self.room["room_id"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_owner_member_roles_and_stable_id(self):
        rooms.join_room(self.db, self.rid, "clawdia")
        self.assertEqual(rooms.member_role(self.db, self.rid, "clawdia"), "user")
        self.assertEqual(rooms.get_room(self.db, self.rid, "clawdia")["role_label"], "member")
        self.assertEqual(rooms.room_by_name(self.db, "dom's agents")["room_id"], self.rid)
        with self.assertRaises(rooms.RoomError):
            rooms.create_room(self.db, "x", "DOM'S AGENTS")

    def test_private_needs_invite_and_invites_work(self):
        priv = rooms.create_room(self.db, "dom", "Private", visibility="private")
        with self.assertRaisesRegex(rooms.RoomError, "invitation"):
            rooms.join_room(self.db, priv["room_id"], "eve")
        rooms.add_member(self.db, priv["room_id"], "dom", "SystemMonitor", "admin")
        self.assertEqual(rooms.member_role(self.db, priv["room_id"], "systemmonitor"), "admin")
        self.assertEqual([r["name"] for r in rooms.list_rooms(self.db, "eve")], ["Dom's Agents"])

    def test_search_by_name_or_topic(self):
        rooms.create_room(self.db, "dom", "OpenLink Testing", topic="remote control")
        self.assertEqual([r["name"] for r in rooms.list_rooms(self.db, "eve", "remote")], ["OpenLink Testing"])
        self.assertEqual([r["name"] for r in rooms.list_rooms(self.db, "eve", "agents")], ["Dom's Agents"])

    def test_history_paging_and_persistence(self):
        for n in range(5):
            rooms.add_message(self.db, self.rid, "dom", f"m{n}")
            time.sleep(0.002)
        page, more = rooms.history(self.db, self.rid, "dom", limit=3)
        self.assertEqual([m["body"] for m in page], ["m2", "m3", "m4"])
        self.assertTrue(more)
        older, more = rooms.history(self.db, self.rid, "dom", limit=3, before=page[0]["sent_at"])
        self.assertEqual([m["body"] for m in older], ["m0", "m1"])
        self.assertFalse(more)

    def test_group_read_receipts(self):
        for u in ("a", "b", "c"):
            rooms.join_room(self.db, self.rid, u)
        msg = rooms.add_message(self.db, self.rid, "dom", "hello all")
        self.assertEqual(rooms.read_by(self.db, self.rid, msg["message_id"]), ([], 3))
        self.assertTrue(rooms.mark_read(self.db, self.rid, "a", msg["message_id"]))
        self.assertIsNone(rooms.mark_read(self.db, self.rid, "a", msg["message_id"]))  # never twice
        rooms.mark_read(self.db, self.rid, "b", msg["message_id"])
        readers, total = rooms.read_by(self.db, self.rid, msg["message_id"])
        self.assertEqual((sorted(readers), total), (["a", "b"], 3))

    def test_mentions_are_members_only(self):
        rooms.join_room(self.db, self.rid, "Clawdia")
        msg = rooms.add_message(self.db, self.rid, "dom", "@clawdia and @nobody, email a@b.com")
        self.assertEqual(msg["mentions"], ["Clawdia"])

    def test_moderation_kick_mute_ban(self):
        rooms.join_room(self.db, self.rid, "mod")
        rooms.join_room(self.db, self.rid, "troll")
        rooms.set_member_role(self.db, self.rid, "dom", "mod", "moderator")
        rooms.mute(self.db, self.rid, "mod", "troll", 10)
        with self.assertRaisesRegex(rooms.RoomError, "muted"):
            rooms.add_message(self.db, self.rid, "troll", "spam")
        rooms.mute(self.db, self.rid, "mod", "troll", 0)
        rooms.add_message(self.db, self.rid, "troll", "ok now")
        with self.assertRaises(rooms.RoomError):
            rooms.kick(self.db, self.rid, "troll", "mod")  # members can't kick
        with self.assertRaises(rooms.RoomError):
            rooms.kick(self.db, self.rid, "mod", "dom")  # nobody kicks a higher role
        rooms.ban(self.db, self.rid, "mod", "troll", "spam")
        with self.assertRaisesRegex(rooms.RoomError, "banned"):
            rooms.join_room(self.db, self.rid, "troll")
        rooms.unban(self.db, self.rid, "mod", "troll")
        rooms.join_room(self.db, self.rid, "troll")

    def test_edit_delete_rules_and_link_removal(self):
        rooms.join_room(self.db, self.rid, "b")
        msg = rooms.add_message(self.db, self.rid, "b", "see https://example.com now")
        with self.assertRaises(rooms.RoomError):
            rooms.edit_message(self.db, self.rid, "c-not-member", msg["message_id"], "x")
        changed, denied = rooms.remove_links(self.db, self.rid, "dom", [{"message_id": msg["message_id"]}], server._find_links)
        self.assertEqual(changed[0]["body"], "see [link removed] now")  # owner moderates
        rooms.delete_message(self.db, self.rid, "b", msg["message_id"])
        self.assertTrue(rooms.history(self.db, self.rid, "dom")[0][-1]["deleted"])

    def test_owner_must_hand_over_before_leaving(self):
        rooms.join_room(self.db, self.rid, "b")
        with self.assertRaises(rooms.RoomError):
            rooms.leave_room(self.db, self.rid, "dom")
        rooms.transfer_ownership(self.db, self.rid, "dom", "b")
        self.assertFalse(rooms.leave_room(self.db, self.rid, "dom"))
        self.assertEqual(rooms.get_room(self.db, self.rid, "b")["owner"], "b")


class RoomServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = server.DB
        server.DB = str(Path(self.tmp.name) / "s.db")
        server.init_db()
        self.pushed = []
        self.p = [mock.patch.object(server, "_send_to_all_sessions", lambda users, p: self.pushed.append((set(u.lower() for u in users), p))),
                  mock.patch.object(server, "_canonical_username", lambda n: str(n or "")),
                  mock.patch.object(server, "_is_admin", lambda u: False)]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()
        server.DB = self.orig
        self.tmp.cleanup()

    def act(self, user, action, **fields):
        sock = FakeSock()
        server._handle_room_action(sock, user, action, dict(fields, action=action))
        return sock

    def test_rooms_are_on_for_everyone(self):
        self.assertTrue(server._can_user_use_feature("anyone", "group_chat"))

    def test_create_post_read_flow(self):
        s = self.act("dom", "group_room_create", name="Thrive Beta")
        rid = s.last("group_room_result")["room"]["room_id"]
        self.act("bob", "group_room_join", room_id=rid)
        self.act("dom", "group_room_message", room_id=rid, body="hi @bob", client_id="c1")
        posted = [p for u, p in self.pushed if p["action"] == "group_room_message"][-1]["message"]
        self.assertEqual((posted["client_id"], posted["mentions"]), ("c1", ["bob"]))
        self.act("bob", "group_room_read", room_id=rid, message_id=posted["message_id"])
        read = [p for u, p in self.pushed if p["action"] == "group_room_read"][-1]
        self.assertEqual(read["username"], "bob")
        opened = self.act("bob", "group_room_open", room_id=rid).last("group_room_open_response")
        self.assertEqual([m["body"] for m in opened["messages"]], ["hi @bob"])

    def test_errors_are_plain_and_go_to_the_asker(self):
        s = self.act("eve", "group_room_message", room_id="nope", body="x")
        self.assertIn("wasn't found", s.last("group_room_result")["reason"])

    def test_agent_answers_in_the_room_when_mentioned(self):
        s = self.act("dom", "group_room_create", name="Dom's Agents")
        rid = s.last("group_room_result")["room"]["room_id"]
        self.act("dom", "group_room_add_member", room_id=rid, username="Clawdia")
        self.act("dom", "group_room_add_member", room_id=rid, username="Tester")
        started = []
        with mock.patch.object(server, "_is_virtual_bot", lambda u: u.lower() == "clawdia"), \
                mock.patch.object(server.threading, "Thread", lambda target, args, **k: mock.Mock(start=lambda: started.append(args))):
            self.act("dom", "group_room_message", room_id=rid, body="no mention here")
            self.assertEqual(started, [])
            self.act("dom", "group_room_message", room_id=rid, body="@Clawdia status please")
            self.assertEqual([a[2] for a in started], ["Clawdia"])
            started.clear()
            self.act("Clawdia", "group_room_message", room_id=rid, body="@Clawdia talking to myself")
            self.assertEqual(started, [])  # agents never answer agents

    def test_room_reply_is_posted_in_the_room(self):
        s = self.act("dom", "group_room_create", name="Room B")
        rid = s.last("group_room_result")["room"]["room_id"]
        self.act("dom", "group_room_add_member", room_id=rid, username="Sophia")
        item = rooms.add_message(server.DB, rid, "dom", "@Sophia hi")
        with mock.patch.object(server, "_room_agent_reply", lambda room, sender, bot, text: f"Hello {sender} from {room['name']}"), \
                mock.patch.object(server, "_is_virtual_bot", lambda u: u.lower() == "sophia"):
            server._room_bot_worker(rid, "dom", "Sophia", item)
        msgs, _ = rooms.history(server.DB, rid, "dom")
        self.assertEqual((msgs[-1]["sender"], msgs[-1]["body"]), ("Sophia", "Hello dom from Room B"))
        self.assertEqual(rooms.read_by(server.DB, rid, item["message_id"])[0], ["Sophia"])


if __name__ == "__main__":
    unittest.main()
