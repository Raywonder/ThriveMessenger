import socket
import sqlite3
import tempfile
import unittest
from pathlib import Path

from srv import server


class LiveBranchAccountDeletionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        server.DB = str(Path(self.temp_dir.name) / "thrive.db")
        server.init_db()

    def tearDown(self):
        server.DB = self.original_db
        self.temp_dir.cleanup()

    def test_delete_removes_credentials_provider_links_and_policy_records(self):
        con = sqlite3.connect(server.DB)
        con.execute("INSERT INTO users(username,password,is_verified) VALUES('alice','hash',1)")
        con.execute("INSERT INTO users(username,password,is_verified) VALUES('bob','hash',1)")
        con.execute("INSERT INTO contacts(owner,contact) VALUES('alice','bob')")
        con.execute("INSERT INTO contacts(owner,contact) VALUES('bob','alice')")
        con.execute("INSERT INTO user_passkeys(id,username,label,token_hash,created_at,revoked) VALUES('p1','alice','Phone','hash','now',0)")
        con.execute("INSERT INTO linked_identities(username,provider,external_id,credential_ref,created_at) VALUES('alice','mastodon','@alice','vault:mastodon/alice','now')")
        con.execute("INSERT INTO wordpress_account_links(thrive_username,wp_user_id) VALUES('alice','10')")
        con.execute("INSERT INTO mastodon_account_links(thrive_username,instance_host,account_id) VALUES('alice','example.social','20')")
        con.execute("INSERT INTO feature_allow_users(feature_key,username) VALUES('voice','alice')")
        con.commit()
        con.close()

        self.assertTrue(server.delete_user_account("ALICE"))

        con = sqlite3.connect(server.DB)
        checks = (
            ("users", "username"),
            ("user_passkeys", "username"),
            ("linked_identities", "username"),
            ("wordpress_account_links", "thrive_username"),
            ("mastodon_account_links", "thrive_username"),
            ("feature_allow_users", "username"),
        )
        for table, column in checks:
            self.assertEqual(con.execute(f"SELECT COUNT(*) FROM {table} WHERE {column}='alice'").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM contacts WHERE owner='alice' OR contact='alice'").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM users WHERE username='bob'").fetchone()[0], 1)
        con.close()

    def test_session_revocation_preserves_response_socket(self):
        response_server, response_client = socket.socketpair()
        other_server, other_client = socket.socketpair()
        try:
            with server.lock:
                server.user_sessions["alice"] = {response_server, other_server}
            server.close_user_sessions("alice", exclude=response_server)
            response_server.sendall(b"ok")
            self.assertEqual(response_client.recv(2), b"ok")
            other_client.settimeout(1)
            self.assertEqual(other_client.recv(1), b"")
        finally:
            with server.lock:
                server.user_sessions.pop("alice", None)
            for item in (response_server, response_client, other_server, other_client):
                try:
                    item.close()
                except OSError:
                    pass


if __name__ == "__main__":
    unittest.main()
