#!/usr/bin/env python3
import argparse
import runpy
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CORE_FILES = (
    "weathercal/__init__.py",
    "weathercal/app.py",
    "weathercal/buttons.py",
    "weathercal/compat.py",
    "weathercal/configuration.py",
    "weathercal/diagnostics.py",
    "weathercal/displays/__init__.py",
    "weathercal/displays/base.py",
    "weathercal/displays/factory.py",
    "weathercal/formatters.py",
    "weathercal/icons.py",
    "weathercal/mqtt_client.py",
    "weathercal/networking.py",
    "weathercal/pages.py",
    "weathercal/scheduler.py",
    "weathercal/state.py",
    "weathercal/timeutil.py",
    "weathercal/topics.py",
)

DRIVER_FILES = {
    "hd44780": (
        "weathercal/displays/character.py",
        "weathercal/displays/hd44780.py",
    ),
    "ili9341": (
        "weathercal/displays/font5x7.py",
        "weathercal/displays/ili9341.py",
    ),
    "serial": ("weathercal/displays/serial.py",),
}


def load_device(config):
    try:
        device = runpy.run_path(str(config)).get("DEVICE")
    except Exception as exc:
        raise SystemExit("could not load DEVICE from {}: {}".format(config, exc))
    if not isinstance(device, dict):
        raise SystemExit("{} must define a DEVICE dictionary".format(config))
    driver = device.get("driver")
    if driver not in DRIVER_FILES:
        raise SystemExit("unsupported display driver in {}: {}".format(config, driver))
    return device


def deployment_files(device, all_drivers=False):
    selected = set(CORE_FILES)
    if all_drivers:
        groups = DRIVER_FILES.values()
    else:
        driver = device["driver"]
        groups = [DRIVER_FILES[driver]]
        if driver != "serial" and device.get("serial_fallback", True):
            groups.append(DRIVER_FILES["serial"])
    for files in groups:
        selected.update(files)
    return tuple(sorted(selected))


def setup_script():
    return (
        "import os\n"
        "for path in ('weathercal', 'weathercal/displays'):\n"
        "    try:\n"
        "        os.mkdir(path)\n"
        "    except OSError:\n"
        "        pass"
    )


def cleanup_script(selected):
    unused = tuple(
        sorted(
            path
            for files in DRIVER_FILES.values()
            for path in files
            if path not in selected
        )
    )
    return (
        "import os\n"
        "for path in {!r}:\n"
        "    try:\n"
        "        os.remove(path)\n"
        "    except OSError:\n"
        "        pass\n"
        "for path in ('weathercal/__pycache__', "
        "'weathercal/displays/__pycache__'):\n"
        "    try:\n"
        "        for name in os.listdir(path):\n"
        "            os.remove(path + '/' + name)\n"
        "        os.rmdir(path)\n"
        "    except OSError:\n"
        "        pass"
    ).format(unused)


def deploy(
    config,
    secrets,
    device=None,
    all_drivers=False,
    reset=None,
    input_fn=input,
    which=shutil.which,
    run=subprocess.run,
):
    if not which("mpremote"):
        raise SystemExit("mpremote is required: python3 -m pip install mpremote")
    for path in (config, secrets):
        if not path.is_file():
            raise SystemExit("file not found: {}".format(path))

    device_config = load_device(config)
    selected = deployment_files(device_config, all_drivers=all_drivers)
    bundle_size = sum((ROOT / path).stat().st_size for path in selected)
    prefix = ["mpremote"]
    if device:
        prefix.extend(["connect", device])
    print(
        "Deploying {} bundle: {} files, {} bytes".format(
            device_config["driver"],
            len(selected),
            bundle_size,
        )
    )
    run([*prefix, "exec", setup_script()], check=True)
    for source, destination in (
        (ROOT / "main.py", ":main.py"),
        (config, ":config.py"),
        (secrets, ":secrets.py"),
    ):
        run([*prefix, "fs", "cp", str(source), destination], check=True)
    for relative_path in selected:
        run(
            [
                *prefix,
                "fs",
                "cp",
                str(ROOT / relative_path),
                ":" + relative_path,
            ],
            check=True,
        )
    run([*prefix, "exec", cleanup_script(selected)], check=True)
    print("Deployment complete.")
    if reset is None:
        answer = input_fn("Reset the Pico W now? [y/N]: ").strip().lower()
        reset = answer in ("y", "yes")
    if reset:
        print("Resetting Pico W")
        run([*prefix, "reset"], check=True)
    else:
        print("Reset skipped; reset the Pico W when ready.")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy weather-cal-micropython with mpremote."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="display profile config to install as config.py",
    )
    parser.add_argument(
        "--secrets",
        type=Path,
        required=True,
        help="Wi-Fi/MQTT secrets file to install as secrets.py",
    )
    parser.add_argument("--device", help="mpremote device selector")
    parser.add_argument(
        "--all-drivers",
        action="store_true",
        help="install every display driver instead of the configured bundle",
    )
    parser.add_argument(
        "--reset",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="reset after copying; prompts when omitted",
    )
    args = parser.parse_args()

    deploy(
        args.config,
        args.secrets,
        args.device,
        all_drivers=args.all_drivers,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
