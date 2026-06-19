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
    def test_deploy_copies_generated_files_and_package(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config = root / "config.py"
            secrets = root / "secrets.py"
            config.write_text("DEVICE = {}", encoding="utf-8")
            secrets.write_text("WIFI_SSID = 'wifi'", encoding="utf-8")
            run = mock.Mock()

            deploy_tool.deploy(
                config,
                secrets,
                device="/dev/ttyACM0",
                reset=False,
                which=lambda command: "/usr/bin/mpremote",
                run=run,
            )

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            commands[0],
            [
                "mpremote",
                "connect",
                "/dev/ttyACM0",
                "fs",
                "cp",
                str(ROOT / "main.py"),
                ":main.py",
            ],
        )
        self.assertEqual(commands[-2][-1], ":secrets.py")
        self.assertEqual(commands[-1][-3:], ["-r", str(ROOT / "weathercal"), ":"])

    def test_deploy_prompts_and_resets_when_confirmed(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config = root / "config.py"
            secrets = root / "secrets.py"
            config.write_text("DEVICE = {}", encoding="utf-8")
            secrets.write_text("WIFI_SSID = 'wifi'", encoding="utf-8")
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
            root = Path(temporary_dir)
            config = root / "config.py"
            secrets = root / "secrets.py"
            config.write_text("DEVICE = {}", encoding="utf-8")
            secrets.write_text("WIFI_SSID = 'wifi'", encoding="utf-8")
            run = mock.Mock()

            deploy_tool.deploy(
                config,
                secrets,
                reset=False,
                which=lambda command: "/usr/bin/mpremote",
                run=run,
            )

        self.assertNotIn("reset", [part for call in run.call_args_list for part in call.args[0]])
