import base64
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

try:
    import main
except Exception as exc:  # wxPython missing on a headless runner
    main = None
    IMPORT_ERROR = exc


class FakeKeyring:
    def __init__(self):
        self.store = {}
    def get_password(self, service, account):
        return self.store.get((service, account))
    def set_password(self, service, account, value):
        self.store[(service, account)] = value
    def delete_password(self, service, account):
        self.store.pop((service, account), None)


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class CredentialKeychainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "user_settings.json")
        self.kr = FakeKeyring()
        self.patches = [
            mock.patch.object(main, "get_settings_path", return_value=self.path),
            mock.patch.object(main, "keyring", self.kr),
            mock.patch.object(main, "log_event", lambda *a, **k: None),
        ]
        for p in self.patches:
            p.start()
        main._KEYRING_UNAVAILABLE[0] = False
        main._KEYRING_WRITE_CACHE.clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        main._KEYRING_UNAVAILABLE[0] = False
        self.tmp.cleanup()

    def _file(self):
        with open(self.path) as fh:
            return json.load(fh)

    def test_save_never_writes_password_to_file(self):
        cfg = main.load_user_config()
        cfg.update({"username": "dom", "password": "s3cret-pass", "remember": True})
        main.save_user_config(cfg)
        raw = open(self.path).read()
        self.assertNotIn("s3cret-pass", raw)
        self.assertNotIn(base64.b64encode(b"s3cret-pass").decode(), raw)
        self.assertIn("s3cret-pass", self.kr.store.values())
        self.assertEqual(main.load_user_config()["password"], "s3cret-pass")

    def test_base64_fallback_and_passkeys_migrate_then_leave_the_file(self):
        with open(self.path, "w") as fh:
            json.dump({"username": "dom", "remember": True,
                       "password_fallback": base64.b64encode(b"old-pass").decode(),
                       "passkey_tokens": {"dom@im.tappedin.fm:2005": base64.b64encode(b"pk-token").decode()}}, fh)
        cfg = main.load_user_config()
        self.assertEqual(cfg["password"], "old-pass")
        data = self._file()
        self.assertNotIn("password_fallback", data)
        self.assertEqual(data.get("passkey_tokens"), {})
        self.assertIn("old-pass", self.kr.store.values())
        self.assertEqual(self.kr.store[(main.PASSKEY_KEYRING_SERVICE, "dom@im.tappedin.fm:2005")], "pk-token")

    def test_unavailable_keychain_keeps_fallback_rather_than_losing_it(self):
        with open(self.path, "w") as fh:
            json.dump({"username": "dom", "remember": True, "password_fallback": base64.b64encode(b"keep-me").decode()}, fh)
        broken = mock.Mock(side_effect=RuntimeError("no keychain"))
        with mock.patch.object(self.kr, "set_password", broken), mock.patch.object(self.kr, "get_password", return_value=None):
            cfg = main.load_user_config()
        self.assertEqual(cfg["password"], "keep-me")
        self.assertIn("password_fallback", self._file())

    def test_hanging_keychain_times_out(self):
        def hang(*a):
            time.sleep(5)
        start = time.time()
        with self.assertRaises(TimeoutError):
            main._kr_call(hang, timeout=0.3)
        self.assertLess(time.time() - start, 2)
        self.assertTrue(main._KEYRING_UNAVAILABLE[0])


if __name__ == "__main__":
    unittest.main()
