import tempfile
import unittest
from pathlib import Path

from srv import server


class VoiceCallFeatureGateTests(unittest.TestCase):
    """Prevent unfinished direct-call signalling from becoming user-visible."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db = server.DB
        server.DB = str(Path(self.temp_dir.name) / "server.db")
        server.init_db()

    def tearDown(self):
        server.DB = self.original_db
        self.temp_dir.cleanup()

    def test_direct_calls_remain_hidden_and_unavailable_without_media_engine(self):
        default = server.FEATURE_DEFAULTS["voice_call"]
        self.assertFalse(default["enabled"])
        self.assertFalse(default["ui_visible"])

        policy = server._feature_policy_row("voice_call")
        self.assertFalse(policy["enabled"])
        self.assertFalse(policy["ui_visible"])
        self.assertFalse(server._can_user_use_feature("test-caller", "voice_call"))


if __name__ == "__main__":
    unittest.main()
