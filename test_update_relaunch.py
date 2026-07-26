import os
import tempfile
import unittest

from update_relaunch import resolve_windows_relaunch_executable


class UpdateRelaunchTests(unittest.TestCase):
    def _touch(self, directory, filename):
        path = os.path.join(directory, filename)
        with open(path, "wb"):
            pass
        return path

    def test_prefers_current_frozen_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            current = self._touch(directory, "CustomBuild.exe")
            self._touch(directory, "Indiginous.exe")
            self.assertEqual(
                resolve_windows_relaunch_executable(directory, current, True),
                current,
            )

    def test_finds_indiginous_install(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = self._touch(directory, "Indiginous.exe")
            self.assertEqual(resolve_windows_relaunch_executable(directory), expected)

    def test_supports_legacy_install_name(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = self._touch(directory, "thrive_messenger.exe")
            self.assertEqual(resolve_windows_relaunch_executable(directory), expected)


if __name__ == "__main__":
    unittest.main()
