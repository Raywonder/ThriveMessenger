import ast
import os
import unittest

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")


class CheckForUpdatesMenuTests(unittest.TestCase):
    """Regression: 15.17 lost Help > Check for Updates in a menu refactor."""

    @classmethod
    def setUpClass(cls):
        cls.src = open(MAIN, encoding="utf-8").read()
        cls.tree = ast.parse(cls.src)

    def _calls(self, attr):
        return [n for n in ast.walk(self.tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == attr]

    def test_help_menu_has_check_for_updates_with_alt_p(self):
        labels = []
        for call in self._calls("Append"):
            if isinstance(call.func.value, ast.Name) and call.func.value.id == "help_menu" and len(call.args) >= 2:
                arg = call.args[1]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    labels.append(arg.value)
        self.assertIn("Check for Updates…\tAlt+P", labels)

    def test_menu_item_is_bound_to_the_update_checker(self):
        bound = set()
        for call in self._calls("Bind"):
            if len(call.args) >= 3 and isinstance(call.args[1], ast.Attribute) and isinstance(call.args[2], ast.Attribute):
                bound.add((call.args[1].attr, call.args[2].attr))
        self.assertIn(("on_check_updates_menu", "mi_check_updates"), bound)
        self.assertIn(("on_check_updates_menu", "mi_app_check_updates"), bound)

    def test_menu_handler_is_not_silent(self):
        fn = next(n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef) and n.name == "on_check_updates_menu")
        call = next(n for n in ast.walk(fn) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "on_check_updates")
        silent = [k for k in call.keywords if k.arg == "silent"]
        self.assertTrue(silent and silent[0].value.value is False)

    def test_alt_p_goes_to_the_menu_item_and_is_not_reused(self):
        self.assertIn("(wx.ACCEL_ALT, ord('P'), int(self.check_updates_id))", self.src)
        self.assertEqual(self.src.count("ord('P')"), 1)

    def test_mac_app_menu_entry(self):
        self.assertIn('apple_menu.Insert(1, wx.ID_ANY, "Check for Updates…")', self.src)


if __name__ == "__main__":
    unittest.main()
