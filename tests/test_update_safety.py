import ast
import os
import textwrap
import time
import types
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


class UpdateNeverInterruptsTypingStructureTests(_SourceMixin, unittest.TestCase):
    """Regression: Dom lost an unsent message when a background update check popped a modal dialog mid-typing
    (2026-09-30). The update pipeline must never steal focus from a compose box, and must never restart over
    unsent text without asking."""

    def test_progress_dialog_is_never_app_modal(self):
        body = self._func("_start_update_download", cls_name="MainFrame")
        self.assertNotIn("wx.PD_APP_MODAL", body)

    def test_progress_dialog_is_skipped_entirely_while_typing(self):
        body = self._func("_start_update_download", cls_name="MainFrame")
        self.assertIn("if not app.is_user_busy_typing():", body)
        self.assertIn("progress = None", body)

    def test_download_update_tolerates_no_progress_dialog(self):
        body = self._func("download_update")
        self.assertIn("progress_dlg is not None", body)

    def test_update_available_prompt_defers_while_busy_typing(self):
        body = self._func("_offer_update_when_idle", cls_name="MainFrame")
        self.assertIn("app.is_user_busy_typing()", body)
        self.assertIn("wx.CallLater(self.UPDATE_IDLE_POLL_MS, self._offer_update_when_idle, tag)", body)

    def test_update_available_check_goes_through_the_idle_gate(self):
        body = self._func("on_check_updates", cls_name="MainFrame")
        self.assertIn("self._offer_update_when_idle(tag)", body)
        self.assertNotIn("A new version is available", body)

    def test_notices_defer_while_busy_typing(self):
        body = self._func("_show_update_notice", cls_name="MainFrame")
        self.assertIn("is_user_busy_typing()", body)

    def test_drafts_are_flushed_unconditionally_before_any_install_decision(self):
        body = self._func("_proceed_with_install", cls_name="MainFrame")
        self.assertLess(body.index("self.save_all_drafts()"), body.index("def _ask_and_go"))

    def test_asks_before_installing_when_a_draft_exists(self):
        body = self._func("_proceed_with_install", cls_name="MainFrame")
        self.assertIn("app.has_any_unsent_draft()", body)
        self.assertIn('dlg.SetYesNoLabels("Install &Now", "&Later")', body)

    def test_deferring_keeps_the_download_and_remembers_to_ask_later(self):
        body = self._func("_proceed_with_install", cls_name="MainFrame")
        self.assertIn(
            '''app.user_config['pending_update'] = {"tag": tag, "dest": dest, "use_installer": bool(use_installer)}''',
            body)
        # The downloaded file itself is never touched when deferred -- only the decision is remembered.
        self.assertNotIn("os.remove(dest)", body)

    def test_next_check_resumes_a_pending_download_without_refetching(self):
        body = self._func("on_check_updates", cls_name="MainFrame")
        self.assertIn("pending = app.user_config.get('pending_update')", body)
        self.assertIn("os.path.exists(pending['dest'])", body)
        self.assertIn(
            "self._proceed_with_install(pending.get('tag', ''), pending['dest'], bool(pending.get('use_installer')))",
            body)

    def test_install_and_restart_remembers_the_open_chat_first(self):
        body = self._func("_proceed_with_install", cls_name="MainFrame")
        self.assertLess(body.index("self._save_last_open_chat_for_restart()"),
                         body.index("self._install_and_restart(tag, dest, use_installer)"))

    def test_typing_activity_is_tracked_globally(self):
        body = self._func("_handle_draft_typing", cls_name="ChatPanel")
        self.assertIn("app._last_typing_ts = time.time()", body)

    def test_is_user_busy_typing_checks_recent_activity_and_open_compose_boxes(self):
        body = self._func("is_user_busy_typing", cls_name="ClientApp")
        self.assertIn("_last_typing_ts", body)
        self.assertIn("self.has_open_unsent_text()", body)

    def test_has_any_unsent_draft_also_checks_persisted_drafts(self):
        body = self._func("has_any_unsent_draft", cls_name="ClientApp")
        self.assertIn("_load_drafts()", body)

    def test_relaunch_reopens_the_chat_that_was_active(self):
        body = self._func("_reopen_last_chat_after_launch", cls_name="ClientApp")
        self.assertIn("self.user_config.get('last_open_chat')", body)
        self.assertIn("frame.open_room_chat", body)


def _client_app_methods(names):
    """The real ClientApp methods, even when wx is stubbed (mirrors tests/test_reconnect_outbox.py)."""
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    cls = next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef) and n.name == "ClientApp")
    ns = {}
    for fn in cls.body:
        if isinstance(fn, ast.FunctionDef) and fn.name in names:
            exec(textwrap.dedent(ast.get_source_segment(src, fn)), main.__dict__, ns)
    return ns


class FakeInput:
    def __init__(self, text=""):
        self._text = text

    def GetValue(self):
        return self._text


class FakePanel:
    def __init__(self, text=""):
        self.input_ctrl = FakeInput(text)


class FakeFrame:
    def __init__(self, panels):
        self._panels = panels

    def all_chats(self):
        return self._panels


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class BusyTypingBehaviorTests(unittest.TestCase):
    """Behavioral coverage of the actual decision logic (the same technique test_reconnect_outbox.py uses to
    test ClientApp methods without a live wx GUI)."""

    def make_app(self, panels=(), last_typing_ts=0.0):
        app = types.SimpleNamespace(frame=FakeFrame(list(panels)), _last_typing_ts=last_typing_ts,
                                     UPDATE_TYPING_ACTIVE_WINDOW_SECONDS=8)
        names = ("has_open_unsent_text", "is_user_busy_typing", "has_any_unsent_draft")
        for name, fn in _client_app_methods(names).items():
            setattr(app, name, types.MethodType(fn, app))
        return app

    def setUp(self):
        self._orig_cache = main._DRAFTS_CACHE
        main._DRAFTS_CACHE = {}

    def tearDown(self):
        main._DRAFTS_CACHE = self._orig_cache

    def test_not_busy_when_idle_and_nothing_open(self):
        app = self.make_app()
        self.assertFalse(app.is_user_busy_typing())

    def test_busy_right_after_a_keystroke(self):
        app = self.make_app(last_typing_ts=time.time())
        self.assertTrue(app.is_user_busy_typing())

    def test_not_busy_once_the_typing_window_passes(self):
        app = self.make_app(last_typing_ts=time.time() - 30)
        self.assertFalse(app.is_user_busy_typing())

    def test_busy_when_a_compose_box_has_unsent_text_even_without_a_recent_keystroke(self):
        app = self.make_app(panels=[FakePanel("half-typed message")], last_typing_ts=time.time() - 30)
        self.assertTrue(app.is_user_busy_typing())

    def test_not_busy_when_open_compose_boxes_are_all_empty(self):
        app = self.make_app(panels=[FakePanel(""), FakePanel("   ")], last_typing_ts=time.time() - 30)
        self.assertFalse(app.is_user_busy_typing())

    def test_has_any_unsent_draft_true_for_an_open_compose_box(self):
        app = self.make_app(panels=[FakePanel("hi")])
        self.assertTrue(app.has_any_unsent_draft())

    def test_has_any_unsent_draft_true_for_a_persisted_draft_even_if_nothing_is_open(self):
        main._DRAFTS_CACHE = {"alice": "an old unsent draft"}
        app = self.make_app()
        self.assertTrue(app.has_any_unsent_draft())

    def test_has_any_unsent_draft_false_when_nothing_open_and_nothing_saved(self):
        app = self.make_app()
        self.assertFalse(app.has_any_unsent_draft())


if __name__ == "__main__":
    unittest.main()
