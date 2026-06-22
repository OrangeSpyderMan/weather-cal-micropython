import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "deploy.py"
SPEC = importlib.util.spec_from_file_location("deploy_tool", SCRIPT)
deploy_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy_tool)


class DeployTests(unittest.TestCase):
    def make_files(self, root, device):
        config = root / "config.py"
        secrets = root / "secrets.py"
        config.write_text("DEVICE = {!r}\n".format(device), encoding="utf-8")
        secrets.write_text("WIFI_SSID = 'wifi'\n", encoding="utf-8")
        return config, secrets

    def copy_destinations(self, run):
        return [
            command[-1]
            for command in (call.args[0] for call in run.call_args_list)
            if "cp" in command
        ]

    def test_hd44780_bundle_excludes_ili9341(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            config, secrets = self.make_files(
                Path(temporary_dir),
                {"driver": "hd44780", "serial_fallback": True},
            )
            run = mock.Mock()

            deploy_tool.deploy(
                config,
                secrets,
                device="/dev/ttyACM0",
                reset=False,
                which=lambda command: "/usr/bin/mpremote",
                run=run,
            )

        destinations = self.copy_destinations(run)
        self.assertIn(":weathercal/displays/character.py", destinations)
        self.assertIn(":weathercal/displays/hd44780.py", destinations)
        self.assertIn(":weathercal/displays/serial.py", destinations)
        self.assertNotIn(":weathercal/displays/ili9341.py", destinations)
        self.assertNotIn(":weathercal/displays/font5x7.py", destinations)
        self.assertFalse(any("-r" in call.args[0] for call in run.call_args_list))
        self.assertEqual(
            run.call_args_list[0].args[0][:4],
            ["mpremote", "connect", "/dev/ttyACM0", "exec"],
        )

    def test_ili9341_bundle_excludes_hd44780(self):
        selected = deploy_tool.deployment_files(
            {"driver": "ili9341", "serial_fallback": False}
        )

        self.assertIn("weathercal/displays/ili9341.py", selected)
        self.assertIn("weathercal/displays/font5x7.py", selected)
        self.assertNotIn("weathercal/displays/character.py", selected)
        self.assertNotIn("weathercal/displays/hd44780.py", selected)
        self.assertNotIn("weathercal/displays/serial.py", selected)

    def test_serial_bundle_contains_only_serial_driver(self):
        selected = deploy_tool.deployment_files({"driver": "serial"})

        self.assertIn("weathercal/displays/serial.py", selected)
        self.assertNotIn("weathercal/displays/ili9341.py", selected)
        self.assertNotIn("weathercal/displays/hd44780.py", selected)

    def test_pico_display_2_bundle_contains_driver_and_serial_fallback(self):
        selected = deploy_tool.deployment_files(
            {"driver": "pico_display_2", "serial_fallback": True}
        )

        self.assertIn("weathercal/displays/pico_display_2.py", selected)
        self.assertIn("weathercal/displays/serial.py", selected)
        self.assertNotIn("weathercal/displays/ili9341.py", selected)
        self.assertNotIn("weathercal/displays/hd44780.py", selected)

    def test_all_drivers_bundle_contains_every_driver(self):
        selected = deploy_tool.deployment_files(
            {"driver": "serial"},
            all_drivers=True,
        )

        for files in deploy_tool.DRIVER_FILES.values():
            for path in files:
                self.assertIn(path, selected)

    def test_cleanup_removes_unused_drivers_and_bytecode(self):
        selected = deploy_tool.deployment_files(
            {"driver": "hd44780", "serial_fallback": False}
        )

        script = deploy_tool.cleanup_script(selected)

        self.assertIn("weathercal/displays/ili9341.py", script)
        self.assertIn("weathercal/displays/serial.py", script)
        self.assertNotIn("'weathercal/displays/hd44780.py'", script)
        self.assertIn("weathercal/displays/__pycache__", script)

    def test_deploy_prompts_and_resets_when_confirmed(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            config, secrets = self.make_files(
                Path(temporary_dir),
                {"driver": "serial"},
            )
            run = mock.Mock()

            deploy_tool.deploy(
                config,
                secrets,
                device="/dev/ttyACM0",
                reset=None,
                input_fn=lambda prompt: "y",
                which=lambda command: "/usr/bin/mpremote",
                run=run,
            )

        self.assertEqual(
            run.call_args_list[-1].args[0],
            ["mpremote", "connect", "/dev/ttyACM0", "reset"],
        )

    def test_deploy_can_skip_reset_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            config, secrets = self.make_files(
                Path(temporary_dir),
                {"driver": "serial"},
            )
            run = mock.Mock()

            deploy_tool.deploy(
                config,
                secrets,
                reset=False,
                which=lambda command: "/usr/bin/mpremote",
                run=run,
            )

        self.assertNotIn(
            "reset",
            [part for call in run.call_args_list for part in call.args[0]],
        )
