import importlib.util
import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone


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


class ExternalScheduleTests(unittest.TestCase):
    def test_external_schedule_is_active_until_a_newer_cron_event(self):
        external = datetime(2026, 8, 27, 18, 1, tzinfo=timezone.utc)
        self.assertTrue(
            helpers.external_schedule_is_active(
                external, external - timedelta(minutes=1)
            )
        )
        self.assertFalse(
            helpers.external_schedule_is_active(
                external, external + timedelta(minutes=1)
            )
        )

    def test_external_schedule_remains_active_without_crons(self):
        external = datetime(2026, 8, 27, 18, 1, tzinfo=timezone.utc)
        self.assertTrue(helpers.external_schedule_is_active(external, None))

    def test_persisted_state_reads_legacy_data(self):
        state = helpers.PersistedState.from_dict(
            {"main_state": "AUTO", "expected_state": False, "manual_until": None}
        )
        self.assertIsNotNone(state)
        self.assertIsNone(state.external_schedule_state)
        self.assertIsNone(state.external_schedule_changed_at)

    def test_external_schedule_state_round_trips_through_storage(self):
        changed_at = "2026-08-27T18:01:00+00:00"
        original = helpers.PersistedState(
            "AUTO", False, None, True, changed_at
        )
        restored = helpers.PersistedState.from_dict(original.to_dict())
        self.assertIsNotNone(restored)
        self.assertTrue(restored.external_schedule_state)
        self.assertEqual(restored.external_schedule_changed_at, changed_at)

if __name__ == "__main__":
    unittest.main()
