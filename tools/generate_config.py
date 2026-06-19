#!/usr/bin/env python3
import argparse
import getpass
import os
import pprint
import runpy
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from weathercal.configuration import validate_config  # noqa: E402
from deploy import deploy  # noqa: E402


PROFILES = {
    "ep0164": ROOT / "examples" / "config_ep0164.py",
    "freenove-1602": ROOT / "examples" / "config_freenove_1602.py",
    "freenove-2004": ROOT / "examples" / "config_freenove_2004.py",
    "serial": ROOT / "examples" / "config_serial.py",
}
CONFIG_NAMES = ("DEVICE", "MQTT", "RUNTIME", "BUTTONS", "PAGE_PROFILES")
EP0164_ORIENTATIONS = {
    "portrait": (0, "ep0164-portrait"),
    "landscape": (1, "ep0164-landscape"),
    "portrait-flipped": (2, "ep0164-portrait"),
    "landscape-flipped": (3, "ep0164-landscape"),
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate config.py and secrets.py for Weather Cal."
    )
    parser.add_argument("--profile", choices=sorted(PROFILES))
    parser.add_argument(
        "--orientation",
        choices=sorted(EP0164_ORIENTATIONS),
        help="EP-0164 orientation; flipped variants rotate by 180 degrees",
    )
    parser.add_argument(
        "--serial-plain",
        action="store_true",
        help="disable ANSI screen clearing for the serial profile",
    )
    parser.add_argument("--i2c-id", type=int)
    parser.add_argument("--i2c-sda", type=int)
    parser.add_argument("--i2c-scl", type=int)
    parser.add_argument(
        "--i2c-address",
        type=i2c_address,
        help="LCD backpack address such as 0x27, or auto",
    )
    parser.add_argument("--mqtt-host")
    parser.add_argument("--mqtt-port", type=int)
    parser.add_argument("--mqtt-base-topic")
    parser.add_argument("--mqtt-client-id")
    parser.add_argument("--mqtt-user")
    parser.add_argument("--mqtt-password")
    parser.add_argument("--wifi-ssid")
    parser.add_argument("--wifi-password")
    parser.add_argument("--page-duration", type=float)
    parser.add_argument("--stale-after", type=float)
    parser.add_argument("--config-output", type=Path, default=ROOT / "config.py")
    parser.add_argument(
        "--secrets-output",
        type=Path,
        default=ROOT / "secrets.py",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="require essential values on the command line",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace existing output files",
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="deploy generated files to the Pico W with mpremote",
    )
    parser.add_argument(
        "--device",
        help="mpremote device selector, for example /dev/ttyACM0",
    )
    parser.add_argument(
        "--reset",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="reset after deployment; prompts in interactive mode",
    )
    parser.add_argument(
        "--all-drivers",
        action="store_true",
        help="deploy every display driver instead of the selected profile",
    )
    return parser


def load_profile(name):
    values = runpy.run_path(str(PROFILES[name]))
    return {key: deepcopy(values[key]) for key in CONFIG_NAMES}


def collect_values(args, input_fn=input, password_fn=getpass.getpass):
    profile = args.profile
    if not profile:
        if args.non_interactive:
            raise SystemExit("ERROR: --profile is required with --non-interactive")
        profile = choose_profile(input_fn)

    config = load_profile(profile)
    if profile == "ep0164":
        orientation = args.orientation
        if not orientation and not args.non_interactive:
            orientation = choose_orientation(input_fn)
        orientation = orientation or "landscape"
        rotation, page_profile = EP0164_ORIENTATIONS[orientation]
        config["DEVICE"]["rotation"] = rotation
        config["DEVICE"]["page_profile"] = page_profile
    elif profile == "serial" and args.serial_plain:
        config["DEVICE"]["ansi"] = False
    elif profile.startswith("freenove-"):
        i2c = config["DEVICE"]["i2c"]
        i2c["i2c_id"] = numeric_setting(
            args.i2c_id,
            "I2C bus ID",
            i2c["i2c_id"],
            args.non_interactive,
            input_fn,
        )
        i2c["sda"] = numeric_setting(
            args.i2c_sda,
            "I2C SDA GPIO",
            i2c["sda"],
            args.non_interactive,
            input_fn,
        )
        i2c["scl"] = numeric_setting(
            args.i2c_scl,
            "I2C SCL GPIO",
            i2c["scl"],
            args.non_interactive,
            input_fn,
        )
        if args.i2c_address is not None:
            i2c["address"] = args.i2c_address
        elif not args.non_interactive:
            answer = prompt(
                "I2C address (auto, 0x27, or 0x3f)",
                "auto",
                input_fn,
            )
            i2c["address"] = i2c_address(answer)
    mqtt = config["MQTT"]
    runtime = config["RUNTIME"]

    mqtt["host"] = value(
        args.mqtt_host,
        "MQTT broker host",
        mqtt["host"],
        args.non_interactive,
        input_fn,
        required=True,
    )
    mqtt["port"] = integer_value(
        args.mqtt_port,
        "MQTT broker port",
        mqtt.get("port", 1883),
        args.non_interactive,
        input_fn,
    )
    mqtt["base_topic"] = value(
        args.mqtt_base_topic,
        "MQTT base topic",
        mqtt["base_topic"],
        args.non_interactive,
        input_fn,
    )
    mqtt["client_id"] = value(
        args.mqtt_client_id,
        "MQTT client ID",
        mqtt["client_id"],
        args.non_interactive,
        input_fn,
    )
    if args.page_duration is not None:
        runtime["default_page_duration_s"] = args.page_duration
    elif not args.non_interactive:
        runtime["default_page_duration_s"] = float(
            prompt(
                "Default page duration (seconds)",
                runtime["default_page_duration_s"],
                input_fn,
            )
        )
    if args.stale_after is not None:
        runtime["stale_after_s"] = args.stale_after
    elif not args.non_interactive:
        runtime["stale_after_s"] = float(
            prompt(
                "Mark data stale after (seconds)",
                runtime["stale_after_s"],
                input_fn,
            )
        )

    wifi_ssid = value(
        args.wifi_ssid,
        "Wi-Fi SSID",
        None,
        args.non_interactive,
        input_fn,
        required=True,
    )
    wifi_password = secret_value(
        args.wifi_password,
        "Wi-Fi password",
        args.non_interactive,
        password_fn,
        required=True,
    )
    mqtt_user = optional_value(
        args.mqtt_user,
        "MQTT username (blank for anonymous)",
        args.non_interactive,
        input_fn,
    )
    mqtt_password = None
    if mqtt_user:
        mqtt_password = secret_value(
            args.mqtt_password,
            "MQTT password",
            args.non_interactive,
            password_fn,
            required=False,
        )

    validate_config(config)
    secrets = {
        "WIFI_SSID": wifi_ssid,
        "WIFI_PASSWORD": wifi_password,
        "MQTT_USER": mqtt_user,
        "MQTT_PASSWORD": mqtt_password,
    }
    return profile, config, secrets


def choose_profile(input_fn):
    choices = list(sorted(PROFILES))
    print("Display profiles:")
    for index, name in enumerate(choices, 1):
        print("  {}) {}".format(index, name))
    while True:
        answer = input_fn("Select profile [1]: ").strip() or "1"
        try:
            return choices[int(answer) - 1]
        except (ValueError, IndexError):
            print("Enter a number from 1 to {}.".format(len(choices)))


def choose_orientation(input_fn):
    choices = (
        "landscape",
        "landscape-flipped",
        "portrait",
        "portrait-flipped",
    )
    print("EP-0164 orientations:")
    for index, name in enumerate(choices, 1):
        print("  {}) {}".format(index, name))
    while True:
        answer = input_fn("Select orientation [1]: ").strip() or "1"
        try:
            return choices[int(answer) - 1]
        except (ValueError, IndexError):
            print("Enter a number from 1 to {}.".format(len(choices)))


def value(
    supplied,
    label,
    default,
    non_interactive,
    input_fn,
    required=False,
):
    if supplied is not None:
        return supplied
    if non_interactive:
        if required and not default:
            raise SystemExit(
                "ERROR: {} is required with --non-interactive".format(label)
            )
        return default
    result = prompt(label, default, input_fn)
    if required and not result:
        raise SystemExit("ERROR: {} is required".format(label))
    return result


def optional_value(supplied, label, non_interactive, input_fn):
    if supplied is not None:
        return supplied or None
    if non_interactive:
        return None
    return input_fn("{}: ".format(label)).strip() or None


def secret_value(
    supplied,
    label,
    non_interactive,
    password_fn,
    required,
):
    if supplied is not None:
        return supplied
    if non_interactive:
        if required:
            raise SystemExit(
                "ERROR: {} is required with --non-interactive".format(label)
            )
        return None
    result = password_fn("{}: ".format(label))
    if required and not result:
        raise SystemExit("ERROR: {} is required".format(label))
    return result or None


def integer_value(
    supplied,
    label,
    default,
    non_interactive,
    input_fn,
):
    if supplied is not None:
        result = supplied
    elif non_interactive:
        result = default
    else:
        try:
            result = int(prompt(label, default, input_fn))
        except ValueError:
            raise SystemExit("ERROR: {} must be an integer".format(label))
    if not 1 <= result <= 65535:
        raise SystemExit("ERROR: {} must be from 1 to 65535".format(label))
    return result


def numeric_setting(
    supplied,
    label,
    default,
    non_interactive,
    input_fn,
):
    if supplied is not None:
        return supplied
    if non_interactive:
        return default
    try:
        return int(prompt(label, default, input_fn))
    except ValueError:
        raise SystemExit("ERROR: {} must be an integer".format(label))


def i2c_address(value):
    if value is None or str(value).lower() == "auto":
        return None
    try:
        address = int(str(value), 0)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "I2C address must be auto or an integer such as 0x27"
        )
    if not 0 <= address <= 0x7F:
        raise argparse.ArgumentTypeError("I2C address must be from 0 to 0x7f")
    return address


def prompt(label, default, input_fn):
    suffix = " [{}]".format(default) if default is not None else ""
    result = input_fn("{}{}: ".format(label, suffix)).strip()
    return result if result else default


def render_config(profile, config):
    lines = [
        "# Generated by tools/generate_config.py",
        "# Display profile: {}".format(profile),
        "",
    ]
    for name in CONFIG_NAMES:
        lines.append("{} = {}".format(name, pprint.pformat(config[name], width=88)))
        lines.append("")
    return "\n".join(lines)


def render_secrets(secrets):
    return (
        "# Generated by tools/generate_config.py\n"
        "WIFI_SSID = {!r}\n"
        "WIFI_PASSWORD = {!r}\n"
        "MQTT_USER = {!r}\n"
        "MQTT_PASSWORD = {!r}\n"
    ).format(
        secrets["WIFI_SSID"],
        secrets["WIFI_PASSWORD"],
        secrets["MQTT_USER"],
        secrets["MQTT_PASSWORD"],
    )


def write_outputs(args, profile, config, secrets):
    for path in (args.config_output, args.secrets_output):
        if path.exists() and not args.force:
            raise SystemExit(
                "ERROR: {} exists; use --force to replace it".format(path)
            )
    args.config_output.parent.mkdir(parents=True, exist_ok=True)
    args.secrets_output.parent.mkdir(parents=True, exist_ok=True)
    args.config_output.write_text(
        render_config(profile, config),
        encoding="utf-8",
    )
    args.secrets_output.write_text(
        render_secrets(secrets),
        encoding="utf-8",
    )
    os.chmod(args.secrets_output, 0o600)


def main():
    args = build_parser().parse_args()
    profile, config, secrets = collect_values(args)
    write_outputs(args, profile, config, secrets)
    print("Generated {}".format(args.config_output))
    print("Generated {} (mode 0600)".format(args.secrets_output))
    should_deploy = args.deploy
    if not args.non_interactive and not should_deploy:
        answer = input("Deploy to the Pico W now? [y/N]: ").strip().lower()
        should_deploy = answer in ("y", "yes")
    if should_deploy:
        reset = args.reset
        if args.non_interactive and reset is None:
            reset = False
        deploy(
            args.config_output,
            args.secrets_output,
            device=args.device,
            all_drivers=args.all_drivers,
            reset=reset,
        )
    else:
        print("Review display pins, then deploy with tools/deploy.py.")


if __name__ == "__main__":
    main()
