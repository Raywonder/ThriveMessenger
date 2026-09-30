import unittest
from unittest.mock import MagicMock, patch

try:
    import main
except Exception:
    main = None


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class FindLinksTests(unittest.TestCase):
    def test_same_rules_as_the_server(self):
        text = "see https://example.com/a?b=1, www.test.org and blind.software. Not server.py or a@mail.com. https://example.com/a?b=1"
        self.assertEqual([l["url"] for l in main.find_links(text)],
                         ["https://example.com/a?b=1", "https://www.test.org", "https://blind.software"])

    def test_plain_file_names_and_versions_are_not_links(self):
        self.assertEqual(main.find_links("main.py and notes.txt, v1.2.3"), [])

    def test_trailing_punctuation_is_not_part_of_the_link(self):
        self.assertEqual(main.find_links("Go to https://im.tappedin.fm/downloads!")[0]["raw"], "https://im.tappedin.fm/downloads")


@unittest.skipIf(main is None, "main.py needs wxPython (or a stub) to import")
class LinksListDialogClosesAfterActionTests(unittest.TestCase):
    """Regression test: every action on the links list (Open, Open in browser, Copy link,
    Copy title, Remove link - by button, keyboard or context menu, since they all share these
    methods) must close the dialog and hand focus back to the chat, the same as Escape/Ctrl+W.
    Bug: these actions used to run and leave the list dialog sitting open."""

    def _dialog(self, item=None):
        dlg = main.LinksListDialog.__new__(main.LinksListDialog)
        dlg.chat = MagicMock()
        dlg.items = [item] if item else []
        dlg.list = MagicMock()
        dlg.list.GetSelection.return_value = 0 if item else -1
        dlg.Close = MagicMock()
        return dlg

    def test_open_closes_the_dialog_when_the_link_opens(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        with patch.object(main, "open_link", return_value=True) as opened:
            dlg._open()
        opened.assert_called_once()
        self.assertIs(opened.call_args.kwargs["return_to"], dlg.chat.focus_messages)
        dlg.Close.assert_called_once()

    def test_open_leaves_the_dialog_open_if_the_open_is_cancelled(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        with patch.object(main, "open_link", return_value=False):
            dlg._open()
        dlg.Close.assert_not_called()

    def test_open_in_browser_closes_the_dialog(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        with patch.object(main, "open_link", return_value=True) as opened:
            dlg._open(mode="browser")
        self.assertEqual(opened.call_args.kwargs["mode"], "browser")
        dlg.Close.assert_called_once()

    def test_copy_link_closes_the_dialog(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        with patch.object(main, "copy_text_to_clipboard", return_value=True), \
             patch.object(main, "speak_text"):
            dlg._copy(title=False)
        dlg.Close.assert_called_once()

    def test_copy_title_closes_the_dialog(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        with patch.object(main, "copy_text_to_clipboard", return_value=True), \
             patch.object(main, "speak_text"):
            dlg._copy(title=True)
        dlg.Close.assert_called_once()

    def test_failed_copy_does_not_close_the_dialog(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        with patch.object(main, "copy_text_to_clipboard", return_value=False), \
             patch.object(main, "speak_text"):
            dlg._copy(title=False)
        dlg.Close.assert_not_called()

    def test_remove_link_closes_the_dialog(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        dlg.chat.remove_link_items.return_value = True
        dlg._remove()
        dlg.Close.assert_called_once()

    def test_remove_link_leaves_the_dialog_open_if_not_confirmed(self):
        item = {"url": "https://example.com", "title": "Example"}
        dlg = self._dialog(item)
        dlg.chat.remove_link_items.return_value = False
        dlg._remove()
        dlg.Close.assert_not_called()
        dlg.list.SetFocus.assert_called_once()


if __name__ == "__main__":
    unittest.main()
