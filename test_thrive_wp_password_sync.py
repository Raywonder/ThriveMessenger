import importlib.util
import json
import pathlib
import tempfile
import unittest


SERVER = pathlib.Path(__file__).parent / 'srv' / 'server.py'
spec = importlib.util.spec_from_file_location('thrive_server', SERVER)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class WordPressPasswordSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        server.DB = str(pathlib.Path(self.tmp.name) / 'thrive.db')
        server.wordpress_config = {
            'enabled': True, 'sync_secret': 'test-secret', 'signature_window_seconds': 300,
            'password_sync_url': 'https://wordpress.test/wp-json/thrive-server-sync/v1/password',
            'password_verify_url': 'https://wordpress.test/wp-json/thrive-server-sync/v1/verify-password',
        }
        server.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def password_event(self, password='new-password', nonce='one-time-nonce'):
        payload = {
            'action': 'wordpress_set_password', 'timestamp': str(int(server.time.time())), 'nonce': nonce,
            'wp_user_id': '42', 'username': 'alice', 'email': 'alice@example.test', 'wp_login': 'alice',
            'is_admin': '0', 'origin': 'wordpress', 'password': password,
        }
        payload['password_digest'] = server._wordpress_password_digest(password)
        payload['signature'] = server._wordpress_password_signature('test-secret', payload)
        return payload

    def test_signed_password_event_is_one_time_and_never_echoes(self):
        calls = []
        old_push = server._push_wordpress_password
        server._push_wordpress_password = lambda *args: calls.append(args)
        try:
            event = self.password_event()
            self.assertEqual(server._handle_wordpress_password_sync(event)['status'], 'ok')
            self.assertEqual(calls, [])
            self.assertEqual(server._handle_wordpress_password_sync(event)['status'], 'error')
        finally:
            server._push_wordpress_password = old_push

    def test_provision_uses_the_thrive_password_and_records_link(self):
        captured = {}
        old_urlopen = server.urllib.request.urlopen

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"status":"ok","wp_user_id":"42"}'

        def fake_urlopen(request, timeout):
            captured.update(json.loads(request.data.decode('utf-8')))
            return Response()

        server.urllib.request.urlopen = fake_urlopen
        try:
            server.wordpress_config['provision_url'] = 'https://wordpress.test/wp-json/thrive-server-sync/v1/provision-user'
            self.assertEqual(server._provision_wordpress_user('alice', 'alice@example.test', 'same-password')['status'], 'ok')
        finally:
            server.urllib.request.urlopen = old_urlopen
        self.assertEqual(captured['password'], 'same-password')
        import sqlite3
        with sqlite3.connect(server.DB) as con:
            self.assertEqual(con.execute('SELECT wp_user_id FROM wordpress_account_links WHERE thrive_username="alice"').fetchone()[0], '42')

    def test_login_fallback_verifies_wordpress_then_updates_local_hash(self):
        import sqlite3
        with sqlite3.connect(server.DB) as con:
            con.execute('INSERT INTO users(username,password,email,is_verified) VALUES(?,?,?,1)', ('alice', server._hash_thrive_password('old-password'), 'alice@example.test'))
            con.execute('INSERT INTO wordpress_account_links(thrive_username,wp_user_id,wp_email,wp_login,linked_at,last_sync_at,is_admin_link) VALUES(?,?,?,?,?,?,0)', ('alice', '42', 'alice@example.test', 'alice', 'now', 'now'))
        old_post = server._wordpress_https_json
        server._wordpress_https_json = lambda url, payload: {'status': 'ok', 'matched': payload['password'] == 'new-password'}
        try:
            self.assertTrue(server._wordpress_verify_password('alice', 'new-password'))
            self.assertFalse(server._wordpress_verify_password('alice', 'wrong-password'))
        finally:
            server._wordpress_https_json = old_post


if __name__ == '__main__':
    unittest.main()
