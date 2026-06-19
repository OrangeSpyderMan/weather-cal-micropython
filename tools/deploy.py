#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def deploy(
    config,
    secrets,
    device=None,
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

    prefix = ["mpremote"]
    if device:
        prefix.extend(["connect", device])
    print("Deploying application files")
    for source, destination in (
        (ROOT / "main.py", ":main.py"),
        (config, ":config.py"),
        (secrets, ":secrets.py"),
    ):
        run(
            [*prefix, "fs", "cp", str(source), destination],
            check=True,
        )
    run(
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
        "--reset",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="reset after copying; prompts when omitted",
    )
    args = parser.parse_args()

    deploy(args.config, args.secrets, args.device, reset=args.reset)


if __name__ == "__main__":
    main()
