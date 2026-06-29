import runpy
import unittest
from pathlib import Path

from weathercal.configuration import ConfigError, validate_config


ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def load(self, filename):
        values = runpy.run_path(str(ROOT / "examples" / filename))
        return {
            key: values[key]
            for key in (
                "DEVICE",
                "MQTT",
                "RUNTIME",
                "BUTTONS",
                "PAGE_PROFILES",
            )
        }

    def test_all_example_profiles_validate(self):
        for filename in (
            "config_ep0164.py",
            "config_freenove_1602.py",
            "config_freenove_2004.py",
            "config_pico_display_2.py",
            "config_serial.py",
        ):
            with self.subTest(filename=filename):
                config = self.load(filename)
                self.assertIs(validate_config(config), config)

    def test_rejects_unknown_page_profile(self):
        config = self.load("config_freenove_1602.py")
        config["DEVICE"]["page_profile"] = "missing"

        with self.assertRaisesRegex(ConfigError, "unknown page profile"):
            validate_config(config)

    def test_rejects_character_widget_without_row(self):
        config = self.load("config_freenove_1602.py")
        del config["PAGE_PROFILES"]["lcd1602"][0]["widgets"][0]["row"]

        with self.assertRaisesRegex(ConfigError, "missing row"):
            validate_config(config)

    def test_rejects_invalid_ili9341_rotation(self):
        config = self.load("config_ep0164.py")
        config["DEVICE"]["rotation"] = 4

        with self.assertRaisesRegex(ConfigError, "rotation"):
            validate_config(config)

    def test_rejects_invalid_pico_display_2_settings(self):
        config = self.load("config_pico_display_2.py")
        config["DEVICE"]["rotation"] = 90
        with self.assertRaisesRegex(ConfigError, "0 or 180"):
            validate_config(config)

        config = self.load("config_pico_display_2.py")
        config["DEVICE"]["backlight"] = 1.5
        with self.assertRaisesRegex(ConfigError, "backlight"):
            validate_config(config)

    def test_rejects_invalid_message_mode(self):
        config = self.load("config_pico_display_2.py")
        config["RUNTIME"]["message_mode"] = "stream"

        with self.assertRaisesRegex(ConfigError, "message_mode"):
            validate_config(config)
