import ast
import os
import shutil
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    import main
except Exception:
    main = None


class _SourceMixin:
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


class DraftStoreStructureTests(_SourceMixin, unittest.TestCase):
    """Regression: Dom lost an unfinished message; drafts must survive a chat close, an app exit, and an
    update-triggered restart (2026-09-30)."""

    def test_drafts_are_stored_next_to_settings(self):
        body = self._func("get_drafts_path")
        self.assertIn("get_config_dir()", body)
        self.assertIn("drafts.json", body)

    def test_writes_are_atomic(self):
        body = self._func("_save_drafts_to_disk")
        self.assertIn(".tmp", body)
        self.assertIn("os.replace(tmp, path)", body)

    def test_set_draft_clears_on_empty_text(self):
        body = self._func("set_draft")
        self.assertIn("drafts.pop(key, None)", body)

    def test_turning_setting_off_forgets_existing_drafts(self):
        self.assertIn("if prev_remember_drafts and not new_remember_drafts:", self.src)
        self.assertIn("clear_all_drafts()", self.src)
        # A fresh load_user_config() also self-heals if the setting was already off on disk.
        body = self._func("load_user_config")
        self.assertIn("if not settings['remember_drafts']:", body)

    def test_default_is_on(self):
        self.assertIn("'remember_drafts': True,", self.src)

    def test_settings_dialog_has_the_checkbox(self):
        self.assertIn('label="Remember unsent messages as drafts"', self.src)

    def test_chat_panel_restores_draft_before_focusing(self):
        body = self._func("__init__", cls_name="ChatPanel")
        self.assertLess(body.index("self._restore_draft()"), body.index("self._focus_input()"))

    def test_restore_uses_changevalue_so_it_never_sends_a_typing_indicator(self):
        body = self._func("_restore_draft", cls_name="ChatPanel")
        self.assertIn("ChangeValue", body)

    def test_draft_cleared_on_send(self):
        body = self._func("on_send", cls_name="ChatPanel")
        self.assertIn("self.clear_draft_now()", body)
        body = self._func("on_send", cls_name="RoomChatPanel")
        self.assertIn("self.clear_draft_now()", body)

    def test_draft_flushed_when_chat_closes(self):
        body = self._func("close_chat", cls_name="ChatPanel")
        self.assertIn("self.flush_draft_now()", body)

    def test_typing_is_debounced_not_saved_on_every_keystroke(self):
        body = self._func("_handle_draft_typing", cls_name="ChatPanel")
        self.assertIn("_draft_timer", body)
        self.assertIn("DRAFT_DEBOUNCE_MS", body)

    def test_room_chat_panel_keys_drafts_by_room_id(self):
        # RoomChatPanel.contact is "room:" + room_id (set in __init__), reused for drafts via self.contact.
        body = self._func("__init__", cls_name="RoomChatPanel")
        self.assertIn('"room:" + self.room_id', body)

    def test_contact_list_shows_draft_indicator(self):
        body = self._func("_apply_search_filter", cls_name="MainFrame")
        self.assertIn('draft_preview(c["user"])', body)
        self.assertIn("Draft:", body)

    def test_room_list_shows_draft_indicator(self):
        body = self._func("_label", cls_name="GroupRoomsPanel")
        self.assertIn('draft_preview("room:"', body)
        self.assertIn("Draft:", body)

    def test_update_restart_flushes_all_open_drafts_first(self):
        body = self._func("_proceed_with_install", cls_name="MainFrame")
        self.assertIn("self.save_all_drafts()", body)

    def test_save_all_drafts_flushes_every_open_chat(self):
        body = self._func("save_all_drafts", cls_name="MainFrame")
        self.assertIn("panel.flush_draft_now()", body)


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class DraftStoreRoundTripTests(unittest.TestCase):
    """Real behavioral coverage of the drafts.json store (runs on a machine with wxPython installed)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_get_config_dir = main.get_config_dir
        main.get_config_dir = lambda: self.tmpdir
        self._orig_cache = main._DRAFTS_CACHE
        main._DRAFTS_CACHE = None

    def tearDown(self):
        main.get_config_dir = self._orig_get_config_dir
        main._DRAFTS_CACHE = self._orig_cache
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_set_then_get(self):
        main.set_draft("alice", "hey are you free later")
        self.assertEqual(main.get_draft("alice"), "hey are you free later")

    def test_persists_across_a_fresh_load(self):
        main.set_draft("alice", "hello there")
        main._DRAFTS_CACHE = None  # simulate a fresh process re-reading the file
        self.assertEqual(main.get_draft("alice"), "hello there")

    def test_atomic_write_leaves_no_tmp_file_behind(self):
        main.set_draft("bob", "draft text")
        path = main.get_drafts_path()
        self.assertTrue(os.path.exists(path))
        self.assertFalse(os.path.exists(path + ".tmp"))

    def test_empty_text_clears_the_draft(self):
        main.set_draft("carol", "something")
        main.set_draft("carol", "   ")
        self.assertEqual(main.get_draft("carol"), "")

    def test_clear_draft(self):
        main.set_draft("dave", "unsent text")
        main.clear_draft("dave")
        self.assertEqual(main.get_draft("dave"), "")

    def test_room_and_dm_ids_do_not_collide(self):
        main.set_draft("general", "a dm to someone named general")
        main.set_draft("room:general", "a room draft")
        self.assertEqual(main.get_draft("general"), "a dm to someone named general")
        self.assertEqual(main.get_draft("room:general"), "a room draft")

    def test_draft_preview_truncates_with_ellipsis(self):
        main.set_draft("erin", "one two three four five six seven eight")
        self.assertEqual(main.draft_preview("erin", max_words=3), "one two three…")

    def test_draft_preview_empty_when_no_draft(self):
        self.assertEqual(main.draft_preview("nobody"), "")

    def test_clear_all_drafts(self):
        main.set_draft("frank", "text")
        main.clear_all_drafts()
        self.assertEqual(main.get_draft("frank"), "")


if __name__ == "__main__":
    unittest.main()
