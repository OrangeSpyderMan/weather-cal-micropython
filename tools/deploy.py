#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    args = parser.parse_args()

    if not shutil.which("mpremote"):
        raise SystemExit("mpremote is required: python3 -m pip install mpremote")
    for path in (args.config, args.secrets):
        if not path.is_file():
            raise SystemExit("file not found: {}".format(path))

    prefix = ["mpremote"]
    if args.device:
        prefix.extend(["connect", args.device])
    print("Deploying application files")
    for source, destination in (
        (ROOT / "main.py", ":main.py"),
        (args.config, ":config.py"),
        (args.secrets, ":secrets.py"),
    ):
        subprocess.run(
            [*prefix, "fs", "cp", str(source), destination],
            check=True,
        )
    subprocess.run(
        [
            *prefix,
            "fs",
            "cp",
            "-r",
            str(ROOT / "weathercal"),
            ":",
        ],
        check=True,
    )
    print("Deployment complete. Reset the Pico W to start.")


if __name__ == "__main__":
    main()
