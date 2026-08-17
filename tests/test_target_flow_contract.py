import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "timed_switch"


class TargetFlowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow = (COMPONENT / "config_flow.py").read_text()
        cls.strings = json.loads((COMPONENT / "strings.json").read_text())

    def test_existing_target_modes_remain_available(self):
        self.assertIn('"built_in_virtual"', self.flow)
        self.assertIn('"existing_entity"', self.flow)

    def test_new_virtual_switch_is_optional(self):
        self.assertIn('async_get_integration(self.hass, "virtual_switch")', self.flow)
        self.assertIn("except IntegrationNotFound", self.flow)
        self.assertIn('menu_options.append("new_virtual_switch")', self.flow)

    def test_new_virtual_switch_uses_its_import_flow(self):
        self.assertIn("flow.async_init(", self.flow)
        self.assertIn('"virtual_switch"', self.flow)
        self.assertIn("config_entries.SOURCE_IMPORT", self.flow)
        self.assertIn('f"switch.{slugify(virtual_name)}_main"', self.flow)

    def test_all_target_menu_options_have_ui_translations(self):
        options = self.strings["config"]["step"]["target"]["menu_options"]
        self.assertEqual(
            {"built_in_virtual", "existing_entity", "new_virtual_switch"}, set(options)
        )


if __name__ == "__main__":
    unittest.main()
