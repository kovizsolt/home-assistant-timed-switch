import importlib.util
import os
import sys
import types
import unittest


PKG_DIR = os.path.join(
    os.path.dirname(__file__), "..", "custom_components", "timed_switch"
)
PKG_NAME = "_timed_switch_cron_under_test"

pkg = types.ModuleType(PKG_NAME)
pkg.__path__ = [PKG_DIR]
sys.modules[PKG_NAME] = pkg

croniter_module = types.ModuleType("croniter")
croniter_module.croniter = object
sys.modules.setdefault("croniter", croniter_module)

spec = importlib.util.spec_from_file_location(
    f"{PKG_NAME}.helpers", os.path.join(PKG_DIR, "helpers.py")
)
helpers = importlib.util.module_from_spec(spec)
helpers.__package__ = PKG_NAME
sys.modules[spec.name] = helpers
spec.loader.exec_module(helpers)


class CronNormalizationTests(unittest.TestCase):
    def test_short_expressions_are_completed_with_wildcards(self):
        self.assertEqual(helpers.normalize_cron_list("0 7"), "0 7 * * *")
        self.assertEqual(helpers.normalize_cron_list("0 7 * *"), "0 7 * * *")

    def test_five_field_expression_is_unchanged(self):
        self.assertEqual(helpers.normalize_cron_list("0 7 * * *"), "0 7 * * *")

    def test_extra_wildcards_are_discarded(self):
        self.assertEqual(helpers.normalize_cron_list("0 7 * * * *"), "0 7 * * *")
        self.assertEqual(helpers.normalize_cron_list("0 7 * * * * *"), "0 7 * * *")

    def test_extra_non_wildcard_field_is_rejected(self):
        with self.assertRaises(helpers.CronFieldCountError):
            helpers.normalize_cron_list("0 7 * * * 1")

    def test_each_expression_is_normalized_independently(self):
        value = "0 7, 30 8 * *\n15 9 * * * * # comment"
        self.assertEqual(
            helpers.normalize_cron_list(value),
            "0 7 * * *, 30 8 * * *\n15 9 * * * # comment",
        )

    def test_empty_and_comment_only_lines_are_preserved(self):
        self.assertEqual(
            helpers.normalize_cron_list("# morning\n\n0 7"),
            "# morning\n\n0 7 * * *",
        )


if __name__ == "__main__":
    unittest.main()
