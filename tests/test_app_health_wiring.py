import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class AppHealthWiringTests(unittest.TestCase):
    """Updates and errors reach the app-health collector; network trouble stays quiet (rules 2026-09-28)."""

    @classmethod
    def setUpClass(cls):
        cls.src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
        cls.tree = ast.parse(cls.src)

    def _func(self, name):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.get_source_segment(self.src, node)
        self.fail(name + " not found")

    def test_client_file_is_bundled_next_to_main(self):
        self.assertTrue(os.path.exists(os.path.join(ROOT, "app_health.py")))
        self.assertIn("from app_health import AppHealth", self.src)

    def test_startup_reports_last_update(self):
        body = self._func("_start_app_health")
        self.assertIn('AppHealth("thrive", APP_HEALTH_KEY, VERSION_TAG', body)
        self.assertIn("HEALTH.on_startup()", body)
        self.assertIn("send_app_health", body)
        self.assertIn("sys.excepthook", body)

    def test_update_started_is_recorded_before_installing(self):
        # 15.23: the actual install call moved out of _start_update_download into _install_and_restart, so an
        # update-ready-but-unsent-draft can ask "install now or later?" (_proceed_with_install) in between.
        # The ordering guarantee (update_started recorded before anything installs) still holds across that
        # call chain.
        body = self._func("_start_update_download")
        self.assertLess(body.index("HEALTH.update_started(tag)"), body.index("self._proceed_with_install(tag, dest, use_installer)"))
        install_body = self._func("_install_and_restart")
        self.assertIn("apply_installer_update(dest)", install_body)
        self.assertIn('HEALTH.update_failed("install"', install_body)
        body = self._func("_start_update_download")
        self.assertIn("update_failed(stage, error", body)

    def test_unreachable_update_server_is_not_up_to_date(self):
        body = self._func("check_for_update")
        self.assertIn("if not reached and failures:", body)
        self.assertIn("Thrive couldn't reach the update server.", body)

    def test_network_failures_retry_quietly_with_backoff(self):
        self.assertIn("UPDATE_RETRY_MINUTES = (5, 30, 120)", self.src)
        body = self._func("on_check_updates")
        self.assertIn('if cls == "network":', body)
        self.assertIn("self._schedule_update_retry()", body)

    def test_download_resumes_with_range(self):
        body = self._func("download_update")
        self.assertIn('headers["Range"] = f"bytes={have}-"', body)
        self.assertIn('dest + ".part"', body)
        self.assertIn("os.replace(part, dest)", body)

    def test_diagnostics_go_to_collector_without_user_name(self):
        body = self._func("submit_logs_payload")
        self.assertIn("HEALTH.submit_diagnostics", body)
        self.assertNotIn("username", body)
        self.assertNotIn("DEFAULT_LOG_SUBMIT_URL", self.src)

    def test_privacy_toggle_in_settings(self):
        self.assertIn('label="Send update results and error reports (no personal content)"', self.src)
        self.assertIn("'send_app_health': True,", self.src)


if __name__ == "__main__":
    unittest.main()
