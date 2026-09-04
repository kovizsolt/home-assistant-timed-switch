import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "timed_switch"


class DashboardContractTests(unittest.TestCase):
    def test_cron_ticker_is_monotonic_and_realigns_to_each_minute_boundary(self):
        controller = (COMPONENT / "controller.py").read_text()
        self.assertNotIn("async_track_time_change", controller)
        self.assertIn("async_call_later", controller)
        callback = controller.index("async def _async_cron_timer_fired")
        reschedule = controller.index("self._schedule_next_cron_tick()", callback)
        evaluation = controller.index("await self._async_cron_tick", callback)
        self.assertLess(reschedule, evaluation)

    def test_UI1_frontend_is_an_integration_dependency(self):
        manifest = json.loads((COMPONENT / "manifest.json").read_text())
        self.assertIn("frontend", manifest["dependencies"])
        self.assertIn("lovelace", manifest["dependencies"])

    def test_UI2_card_is_served_and_loaded_automatically(self):
        init_source = (COMPONENT / "__init__.py").read_text()
        self.assertIn("async_register_static_paths", init_source)
        self.assertIn("async_create_item", init_source)
        self.assertIn("async_update_item", init_source)
        self.assertIn("?v={card_version}", init_source)
        self.assertTrue((COMPONENT / "www" / "timed-switch-card.js").is_file())

    def test_UI3_card_discovers_the_complete_device_view(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        for suffix in (
            "_expected",
            "_timed_state",
            "_is_manual_mode",
            "_device",
            "_manual_remaining",
            "_sync_remaining",
            "_manual_timeout",
            "_sync_interval",
            "_on_crons",
            "_off_crons",
            "_status",
            "_since_last_change",
            "_device_last_changed",
            "_timed_state_last_changed",
        ):
            self.assertIn(suffix, card)

    def test_UI4_card_is_available_in_the_picker(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("window.customCards", card)
        self.assertIn("getEntitySuggestion", card)
        self.assertIn('type: "timed-switch-card"', card)

    def test_UI4b_card_has_a_filtered_graphical_editor(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("static getConfigForm()", card)
        self.assertIn('filter: { domain: "switch", integration: "timed_switch" }', card)
        self.assertIn("static getStubConfig(hass, entities = [], entitiesFill = [])", card)
        self.assertIn("TimedSwitchCard._isExpectedEntity", card)

    def test_UI5_controls_use_native_home_assistant_entity_rows(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("window.loadCardHelpers", card)
        self.assertIn("helpers.createCardElement", card)
        self.assertIn('type: "entities"', card)
        self.assertIn('callService("text", "set_value"', card)

    def test_UI6_card_uses_full_section_width_and_ha_locale(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("columns: 12", card)
        self.assertIn("min_columns: 8", card)
        self.assertNotIn("rows:", card)
        self.assertNotIn("min_rows:", card)
        self.assertIn('type: "datetime", style: "short"', card)
        self.assertNotIn("Intl.DateTimeFormat", card)

    def test_UI7_sync_remaining_is_driven_by_the_sync_deadline(self):
        controller = (COMPONENT / "controller.py").read_text()
        sensor = (COMPONENT / "sensor.py").read_text()
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("def sync_remaining_seconds", controller)
        self.assertIn("self.sync_until = dt_util.utcnow() +", controller)
        self.assertIn("class SyncRemainingSensor", sensor)
        self.assertIn("return self._controller.sync_until", sensor)
        self.assertIn("Date.parse(state.state)", card)

    def test_UI7b_countdowns_tick_only_in_the_browser(self):
        controller = (COMPONENT / "controller.py").read_text()
        sensor = (COMPONENT / "sensor.py").read_text()
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertNotIn("_async_tick_remaining", controller)
        self.assertNotIn("_remaining_ticker_cancel", controller)
        self.assertNotIn("_sync_ticker_cancel", controller)
        self.assertNotIn("timedelta(seconds=1)", controller)
        self.assertIn("_attr_device_class = SensorDeviceClass.TIMESTAMP", sensor)
        self.assertIn("setInterval(() => this._render(), 1000)", card)
        self.assertIn("Math.floor((deadline - Date.now()) / 1000)", card)
        self.assertIn("delete displayAttributes.device_class", card)
        self.assertIn("attributes: displayAttributes", card)
        self.assertIn('return "--:--"', card)

    def test_integration_entries_are_visible_on_the_integrations_dashboard(self):
        self.assertEqual(
            json.loads((COMPONENT / "manifest.json").read_text())["integration_type"],
            "device",
        )

    def test_UI8_empty_time_values_have_readable_placeholders(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        switch = (COMPONENT / "switch.py").read_text()
        self.assertIn('return "--:--"', card)
        self.assertIn('next_schedule else "--"', switch)

    def test_UI9_zero_duration_disables_its_remaining_row(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("class TimedSwitchRemainingRow", card)
        self.assertIn('const disabled = duration === 0', card)
        self.assertIn('this.style.opacity = disabled ? "0.38"', card)
        self.assertIn('this.style.pointerEvents = disabled ? "none"', card)
        self.assertIn('ids.remaining, ids.timeout, "Time Until Override:"', card)
        self.assertIn('ids.syncRemaining, ids.interval, "Time Until Sync:"', card)

    def test_UI10_device_state_follows_target_state(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        target = card.index('ids.expected, "Expected state:"')
        device = card.index('ids.device, "Device state:"')
        manual = card.index('ids.manual, "Manual Override:"')
        self.assertLess(target, device)
        self.assertLess(device, manual)

        switch = (COMPONENT / "switch.py").read_text()
        self.assertIn('SUFFIX_DEVICE, "Device state"', switch)
        self.assertIn('SUFFIX_EXPECTED, "Expected state"', switch)
        self.assertIn('SUFFIX_TIMED_STATE, "Scheduled state"', switch)
        self.assertIn('SUFFIX_IS_MANUAL_MODE, "Manual Override"', switch)

    def test_UI10b_device_page_categories_match_entity_roles(self):
        init_source = (COMPONENT / "__init__.py").read_text()
        switch = (COMPONENT / "switch.py").read_text()
        sensor = (COMPONENT / "sensor.py").read_text()
        self.assertIn(
            'f"switch.{slug}_{SUFFIX_IS_MANUAL_MODE}": None', init_source
        )
        self.assertNotIn(
            "class IsManualModeSwitch(_BaseControllerSwitch):\n"
            '    """switch.<slug>_is_manual_mode — SPEC.md B2.3."""\n\n'
            "    _attr_entity_category",
            switch,
        )
        for class_name in ("ManualRemainingSensor", "SyncRemainingSensor"):
            start = sensor.index(f"class {class_name}")
            end = sensor.find("\nclass ", start + 1)
            class_source = sensor[start : end if end != -1 else None]
            self.assertIn(
                "_attr_entity_category = EntityCategory.DIAGNOSTIC",
                class_source,
            )
        self.assertIn('"Time Until Override"', sensor)
        self.assertIn('"Time Until Sync"', sensor)
        self.assertIn(
            'f"binary_sensor.{slug}_{SUFFIX_STATUS}": EntityCategory.DIAGNOSTIC',
            init_source,
        )
        text_platform = (COMPONENT / "text.py").read_text()
        self.assertIn("class TargetEntityText", text_platform)
        self.assertIn('f"text.{slug}_{SUFFIX_TARGET_ENTITY}"', text_platform)
        self.assertIn(
            'f"text.{slug}_{SUFFIX_TARGET_ENTITY}": EntityCategory.CONFIG',
            init_source,
        )
        self.assertIn("return self._controller.target_entity_id", text_platform)
        self.assertIn("raise ServiceValidationError", text_platform)

    def test_UI10d_problem_entity_is_migrated_to_status(self):
        init_source = (COMPONENT / "__init__.py").read_text()
        binary_sensor = (COMPONENT / "binary_sensor.py").read_text()
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("def _migrate_status_entity", init_source)
        self.assertIn("new_unique_id=f\"{entry_id}_{SUFFIX_STATUS}\"", init_source)
        self.assertIn("class StatusBinarySensor", binary_sensor)
        self.assertIn('`binary_sensor.${objectId}_status`', card)
        self.assertNotIn('`binary_sensor.${objectId}_problem`', card)

    def test_UI10c_three_control_change_timestamps_are_independent(self):
        controller = (COMPONENT / "controller.py").read_text()
        sensor = (COMPONENT / "sensor.py").read_text()
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("self.expected_last_changed", controller)
        self.assertIn("self.timed_state_last_changed", controller)
        self.assertIn("self.device_last_changed", controller)
        self.assertIn("def _set_timed_state", controller)
        self.assertIn("def _set_device_state", controller)
        self.assertIn("if (old.state == STATE_ON) == new_bool:", controller)
        self.assertIn("class TimedStateLastChangedSensor", sensor)
        self.assertIn('ids.deviceChanged, "Device changed:"', card)
        self.assertIn('ids.since, "Expected changed:"', card)
        self.assertIn('ids.timedChanged, "Scheduled state changed:"', card)

    def test_UI11_schedule_lists_are_full_width_multiline_fields(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        text_platform = (COMPONENT / "text.py").read_text()
        self.assertIn('label: "Schedule"', card)
        self.assertIn('document.createElement("textarea")', card)
        self.assertIn('type: "custom:timed-switch-schedule-row"', card)
        self.assertLess(card.index('label: "Schedule"'), card.index('label: "Timing"'))
        self.assertIn('"Schedule ON"', text_platform)
        self.assertIn('"Schedule OFF"', text_platform)

    def test_UI12_schedule_editing_has_visible_save_feedback_and_error_dialog(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn('this._setStatus("saving")', card)
        self.assertIn('this._setStatus("saved")', card)
        self.assertIn('this._setStatus("error")', card)
        self.assertIn('document.createElement("ha-dialog")', card)
        self.assertIn('error?.body?.message || error?.message', card)
        self.assertIn('}, undefined, false)', card)

    def test_UI13_cron_validation_precedes_persistence_and_recalculation(self):
        controller = (COMPONENT / "controller.py").read_text()
        validation = controller.index("croniter(expression, dt_util.now())")
        persistence = controller.index("self._persist_option(key, normalized_value)", validation)
        recalculation = controller.index("await self._async_cron_tick", persistence)
        self.assertLess(validation, persistence)
        self.assertLess(persistence, recalculation)
        self.assertIn("ServiceValidationError", controller)

    def test_UI14_timing_number_values_are_persisted_without_listener_recursion(self):
        controller = (COMPONENT / "controller.py").read_text()
        init_source = (COMPONENT / "__init__.py").read_text()
        for key in ("CONF_MANUAL_TIMEOUT", "CONF_SYNC_INTERVAL"):
            self.assertIn(f"self._persist_option({key}, self.", controller)
        self.assertIn("def _persist_option", controller)
        self.assertIn("async_get_entry(self.entry.entry_id)", controller)
        self.assertIn("async_update_entry(current_entry, options=options)", controller)
        self.assertIn("self._persist_option(key, normalized_value)", controller)
        self.assertIn("controller.entry = updated_entry", init_source)
        self.assertGreaterEqual(init_source.count("persist=False"), 2)


if __name__ == "__main__":
    unittest.main()
