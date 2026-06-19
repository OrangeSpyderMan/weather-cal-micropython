import argparse
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "generate_config.py"
SPEC = importlib.util.spec_from_file_location("generate_config", SCRIPT)
generate_config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_config)


def arguments(**overrides):
    values = {
        "profile": "freenove-1602",
        "orientation": None,
        "serial_plain": False,
        "i2c_id": None,
        "i2c_sda": None,
        "i2c_scl": None,
        "i2c_address": None,
        "mqtt_host": "mqtt.local",
        "mqtt_port": 1883,
        "mqtt_base_topic": "inkplate/weather-calendar",
        "mqtt_client_id": "kitchen-weather",
        "mqtt_user": None,
        "mqtt_password": None,
        "wifi_ssid": "home-wifi",
        "wifi_password": "wifi-secret",
        "page_duration": 12,
        "stale_after": 7200,
        "config_output": Path("config.py"),
        "secrets_output": Path("secrets.py"),
        "non_interactive": True,
        "force": False,
        "deploy": False,
        "device": None,
        "reset": None,
        "all_drivers": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class GenerateConfigTests(unittest.TestCase):
    def test_non_interactive_generation_and_validation(self):
        args = arguments()

        profile, config, secrets = generate_config.collect_values(args)

        self.assertEqual(profile, "freenove-1602")
        self.assertEqual(config["MQTT"]["host"], "mqtt.local")
        self.assertEqual(config["MQTT"]["client_id"], "kitchen-weather")
        self.assertEqual(config["RUNTIME"]["default_page_duration_s"], 12)
        self.assertEqual(config["DEVICE"]["transport"], "pcf8574")
        self.assertEqual(config["DEVICE"]["i2c"]["sda"], 0)
        self.assertIsNone(config["DEVICE"]["i2c"]["address"])
        self.assertEqual(secrets["WIFI_SSID"], "home-wifi")

    def test_interactive_profile_and_credentials(self):
        answers = iter(
            [
                "1",
                "2",
                "broker.local",
                "1884",
                "",
                "weather-screen",
                "10",
                "3600",
                "my-wifi",
                "",
            ]
        )
        args = arguments(
            profile=None,
            mqtt_host=None,
            mqtt_port=None,
            mqtt_base_topic=None,
            mqtt_client_id=None,
            mqtt_user=None,
            wifi_ssid=None,
            wifi_password=None,
            page_duration=None,
            stale_after=None,
            non_interactive=False,
        )

        profile, config, secrets = generate_config.collect_values(
            args,
            input_fn=lambda prompt: next(answers),
            password_fn=lambda prompt: "wifi-secret",
        )

        self.assertEqual(profile, "ep0164")
        self.assertEqual(config["DEVICE"]["rotation"], 3)
        self.assertEqual(
            config["DEVICE"]["page_profile"],
            "ep0164-landscape",
        )
        self.assertEqual(config["MQTT"]["port"], 1884)
        self.assertIsNone(secrets["MQTT_USER"])

    def test_writes_secret_file_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            args = arguments(
                config_output=root / "config.py",
                secrets_output=root / "secrets.py",
            )
            profile, config, secrets = generate_config.collect_values(args)

            generate_config.write_outputs(args, profile, config, secrets)

            self.assertIn(
                "Display profile: freenove-1602",
                args.config_output.read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                "wifi-secret",
                args.config_output.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "wifi-secret",
                args.secrets_output.read_text(encoding="utf-8"),
            )
            self.assertEqual(args.secrets_output.stat().st_mode & 0o777, 0o600)

    def test_refuses_to_replace_existing_files_without_force(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            args = arguments(
                config_output=root / "config.py",
                secrets_output=root / "secrets.py",
            )
            args.config_output.write_text("existing", encoding="utf-8")
            profile, config, secrets = generate_config.collect_values(args)

            with self.assertRaisesRegex(SystemExit, "use --force"):
                generate_config.write_outputs(args, profile, config, secrets)

    def test_requires_essential_values_non_interactively(self):
        args = arguments(wifi_ssid=None)

        with self.assertRaisesRegex(SystemExit, "Wi-Fi SSID is required"):
            generate_config.collect_values(args)

    def test_non_interactive_portrait_flipped_selection(self):
        args = arguments(
            profile="ep0164",
            orientation="portrait-flipped",
        )

        _, config, _ = generate_config.collect_values(args)

        self.assertEqual(config["DEVICE"]["rotation"], 2)
        self.assertEqual(
            config["DEVICE"]["page_profile"],
            "ep0164-portrait",
        )

    def test_serial_plain_disables_ansi_output(self):
        args = arguments(
            profile="serial",
            serial_plain=True,
        )

        _, config, _ = generate_config.collect_values(args)

        self.assertFalse(config["DEVICE"]["ansi"])

    def test_freenove_i2c_overrides(self):
        args = arguments(
            profile="freenove-2004",
            i2c_id=1,
            i2c_sda=6,
            i2c_scl=7,
            i2c_address=0x3F,
        )

        _, config, _ = generate_config.collect_values(args)

        self.assertEqual(
            config["DEVICE"]["i2c"],
            {
                "i2c_id": 1,
                "sda": 6,
                "scl": 7,
                "frequency": 100000,
                "address": 0x3F,
                "backlight": True,
            },
        )

    def test_i2c_address_parser(self):
        self.assertIsNone(generate_config.i2c_address("auto"))
        self.assertEqual(generate_config.i2c_address("0x27"), 0x27)
