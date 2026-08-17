import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "timed_switch"


class DashboardContractTests(unittest.TestCase):
    def test_cron_ticker_is_aligned_to_the_minute_boundary(self):
        controller = (COMPONENT / "controller.py").read_text()
        self.assertIn("async_track_time_change", controller)
        self.assertIn("second=0", controller)

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
            "_manual_timeout",
            "_check_interval",
            "_problem",
            "_since_last_change",
            "_device_last_changed",
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
        self.assertNotIn("callService(", card)

    def test_UI6_card_uses_full_section_width_and_ha_locale(self):
        card = (COMPONENT / "www" / "timed-switch-card.js").read_text()
        self.assertIn("columns: 8", card)
        self.assertNotIn("rows:", card)
        self.assertNotIn("min_rows:", card)
        self.assertIn('type: "datetime", style: "short"', card)
        self.assertNotIn("Intl.DateTimeFormat", card)


if __name__ == "__main__":
    unittest.main()
