import os
import tempfile
import unittest
from unittest import mock

import main


class FilesLayoutTests(unittest.TestCase):
    """Files are kept per person (<Files>/<username>) and per room (<Files>/Rooms/<room>), and old loose files move."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.patch = mock.patch("os.path.expanduser", lambda p: p.replace("~", self.home, 1))
        self.patch.start()
        self.root = main._received_files_dir()
        os.makedirs(self.root)

    def tearDown(self):
        self.patch.stop()

    def _touch(self, path, text="x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)
        return path

    def test_safe_folder_names(self):
        self.assertEqual(main.safe_folder_name('a<b>:c"d/e\\f|g?h*'), "a_b__c_d_e_f_g_h_")
        self.assertEqual(main.safe_folder_name("CON"), "_CON")
        self.assertEqual(main.safe_folder_name("  ..  "), "unknown")
        self.assertEqual(main.safe_folder_name("Dom's Agents."), "Dom's Agents")

    def test_contact_and_room_dirs(self):
        self.assertEqual(main.contact_files_dir("SystemMonitor"), os.path.join(self.root, "SystemMonitor"))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "SystemMonitor")))
        self.assertEqual(main.room_files_dir("Thrive Beta"), os.path.join(self.root, "Rooms", "Thrive Beta"))

    def test_migration_moves_everything_and_updates_history(self):
        known = self._touch(os.path.join(self.root, "report.txt"))
        by_name = self._touch(os.path.join(self.root, "song.mp3"))
        stray = self._touch(os.path.join(self.root, "old.wav"))
        room_old = self._touch(os.path.join(os.path.dirname(self.root), "room-files", "notes.txt"))
        history = [
            {"direction": "received", "user": "SystemMonitor", "filename": "report.txt", "path": known},
            {"direction": "received", "user": "Clawdia", "filename": "song.mp3", "path": ""},
            {"direction": "sent", "user": "Clawdia", "filename": "mine.doc", "path": "C:/elsewhere/mine.doc"},
        ]
        moved, unknown, changed = main.migrate_files_layout(history)
        self.assertEqual((moved, unknown, changed), (3, 1, True))
        self.assertEqual(history[0]["path"], os.path.join(self.root, "SystemMonitor", "report.txt"))
        self.assertEqual(history[1]["path"], os.path.join(self.root, "Clawdia", "song.mp3"))
        self.assertEqual(history[2]["path"], "C:/elsewhere/mine.doc")  # sent originals are never touched
        self.assertTrue(os.path.isfile(os.path.join(self.root, main.UNKNOWN_SENDER_FOLDER, "old.wav")))
        self.assertTrue(os.path.isfile(os.path.join(self.root, "Rooms", "Earlier room files", "notes.txt")))
        loose = [n for n in os.listdir(self.root) if os.path.isfile(os.path.join(self.root, n))]
        self.assertEqual(loose, [], "nothing left loose in the root")
        self.assertFalse(os.path.exists(os.path.dirname(room_old)), "old room-files folder removed when empty")

    def test_migration_keeps_both_on_name_clash(self):
        self._touch(os.path.join(self.root, "SystemMonitor", "a.txt"), "old")
        src = self._touch(os.path.join(self.root, "a.txt"), "new")
        history = [{"direction": "received", "user": "SystemMonitor", "filename": "a.txt", "path": src}]
        main.migrate_files_layout(history)
        self.assertEqual(history[0]["path"], os.path.join(self.root, "SystemMonitor", "a (1).txt"))
        with open(os.path.join(self.root, "SystemMonitor", "a.txt")) as fh:
            self.assertEqual(fh.read(), "old")

    def test_received_files_can_still_be_removed_from_subfolders(self):
        path = self._touch(os.path.join(main.contact_files_dir("x"), "f.txt"))
        with mock.patch.object(main, "_move_to_trash", lambda p: os.remove(p) or True):
            self.assertEqual(main.remove_received_files([path]), 1)


if __name__ == "__main__":
    unittest.main()
