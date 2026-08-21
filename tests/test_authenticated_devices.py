import datetime
import sqlite3
import tempfile
import unittest
from pathlib import Path

from srv import server


class AuthenticatedDeviceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        server.DB = str(Path(self.temp_dir.name) / "server.db")
        server.init_db()

    def tearDown(self):
        server.DB = self.original_db
        self.temp_dir.cleanup()

    def test_register_lists_and_renews_one_record_per_device(self):
        con = sqlite3.connect(server.DB)
        first = server.register_authenticated_device(con, "alice", {
            "device_id": "phone-1", "device_name": "Alice's iPhone",
            "platform": "iOS", "session_duration": "week",
        })
        second = server.register_authenticated_device(con, "alice", {
            "device_id": "phone-1", "device_name": "Alice's iPhone",
            "platform": "iOS", "session_duration": "year",
        })
        con.close()
        self.assertNotEqual(first, second)
        devices = server.list_authenticated_devices("alice", second)
        self.assertEqual(len(devices), 1)
        self.assertTrue(devices[0]["current"])
        self.assertEqual(devices[0]["device_name"], "Alice's iPhone")

    def test_forever_has_no_expiration_and_selective_revoke_is_scoped(self):
        con = sqlite3.connect(server.DB)
        alice = server.register_authenticated_device(con, "alice", {"device_id": "a", "session_duration": "forever"})
        bob = server.register_authenticated_device(con, "bob", {"device_id": "b", "session_duration": "day"})
        con.close()
        self.assertIsNone(server.list_authenticated_devices("alice")[0]["expires_at"])
        self.assertFalse(server.revoke_authenticated_device("alice", bob))
        self.assertTrue(server.revoke_authenticated_device("alice", alice))
        self.assertEqual(server.list_authenticated_devices("alice"), [])
        self.assertEqual(len(server.list_authenticated_devices("bob")), 1)

    def test_expired_devices_are_not_reported(self):
        con = sqlite3.connect(server.DB)
        con.execute(
            "INSERT INTO authenticated_devices(session_id,username,device_id,device_name,authenticated_at,last_seen_at,expires_at) VALUES(?,?,?,?,?,?,?)",
            ("old", "alice", "old", "Old PC", "2020-01-01T00:00:00Z", "2020-01-01T00:00:00Z", "2020-01-02T00:00:00Z"),
        )
        con.commit(); con.close()
        self.assertEqual(server.list_authenticated_devices("alice"), [])


if __name__ == "__main__":
    unittest.main()
