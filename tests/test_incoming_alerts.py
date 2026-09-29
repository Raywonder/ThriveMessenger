import ast
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class IncomingMessageAlertTests(unittest.TestCase):
    """Regression: agent updates arriving in the chat in front were added silently and marked read (15.18)."""

    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
        cls.tree = ast.parse(cls.src)

    def _func(self, name, cls_name=None):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and cls_name and node.name == cls_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == name:
                        return ast.get_source_segment(self.src, item)
            if not cls_name and isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.get_source_segment(self.src, node)
        self.fail(f"{name} not found")

    def test_open_chat_default_reads_new_messages(self):
        self.assertIn("'open_chat_new_message': 'read',", self.src)

    def test_active_chat_needs_foreground_and_someone_at_the_computer(self):
        body = self._func("is_active_chat", "ChatWindow")
        self.assertIn("window_in_foreground(self)", body)
        self.assertIn("system_idle_seconds() < IDLE_AWAY_SECONDS", body)

    def test_focused_chat_plays_sound_and_speaks(self):
        body = self._func("receive_message")
        self.assertIn("open_chat_new_message", body)
        self.assertIn('app.play_sound("receive.wav")', body)
        self.assertIn("list_follows", body)

    def test_notify_also_speaks(self):
        body = self._func("receive_message")
        self.assertRegex(body, r"show_notification\(\"New message\".*\n(.*\n){0,3}.*speak_text\(f\"New message from")

    def test_toast_app_id_matches_process_and_shortcut(self):
        proc = re.search(r"SetCurrentProcessExplicitAppUserModelID\('([^']+)'\)", self.src).group(1)
        toast = re.search(r'_WinNotification\(app_id="([^"]+)"', self.src).group(1)
        iss = open(os.path.join(ROOT, "thrive_messenger_installer.iss"), encoding="utf-8").read()
        self.assertEqual(proc, toast)
        self.assertIn(f'AppUserModelID: "{proc}"', iss)

    def test_periodic_update_check(self):
        self.assertIn("UPDATE_CHECK_INTERVAL_MS", self.src)
        self.assertIn("self._update_timer.Start(UPDATE_CHECK_INTERVAL_MS)", self.src)


if __name__ == "__main__":
    unittest.main()
