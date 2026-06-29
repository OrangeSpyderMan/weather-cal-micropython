DISPLAY_TYPES = ("ili9341", "pico_display_2", "hd44780", "serial")
BUTTON_ACTIONS = ("previous", "next", "home", "pause")


class ConfigError(ValueError):
    pass


def validate_config(config):
    required = ("DEVICE", "MQTT", "RUNTIME", "BUTTONS", "PAGE_PROFILES")
    for name in required:
        if name not in config:
            raise ConfigError("missing {}".format(name))

    device = config["DEVICE"]
    display_type = device.get("driver")
    if display_type not in DISPLAY_TYPES:
        raise ConfigError("unsupported DEVICE.driver: {}".format(display_type))
    if display_type == "ili9341" and device.get("rotation", 1) not in (0, 1, 2, 3):
        raise ConfigError("DEVICE.rotation must be 0, 1, 2, or 3")
    if display_type == "pico_display_2":
        if device.get("rotation", 0) not in (0, 180):
            raise ConfigError("DEVICE.rotation must be 0 or 180")
        backlight = device.get("backlight", 0.7)
        if not isinstance(backlight, (int, float)) or not 0 <= backlight <= 1:
            raise ConfigError("DEVICE.backlight must be from 0.0 to 1.0")
    if display_type == "hd44780":
        transport = device.get("transport", "gpio")
        if transport not in ("gpio", "pcf8574"):
            raise ConfigError("unsupported HD44780 transport: {}".format(transport))
        if transport == "pcf8574":
            i2c = device.get("i2c", {})
            for key in ("sda", "scl"):
                if key not in i2c:
                    raise ConfigError("DEVICE.i2c.{} is required".format(key))
            address = i2c.get("address")
            if address is not None and not 0 <= address <= 0x7F:
                raise ConfigError("DEVICE.i2c.address must be 0..0x7f")
    profile_name = device.get("page_profile")
    if profile_name not in config["PAGE_PROFILES"]:
        raise ConfigError("unknown page profile: {}".format(profile_name))

    mqtt = config["MQTT"]
    for name in ("host", "base_topic", "client_id"):
        if not mqtt.get(name):
            raise ConfigError("MQTT.{} is required".format(name))
    diagnostics = mqtt.get("diagnostics", {})
    if diagnostics.get("enabled", True):
        _positive(diagnostics, "status_interval_s", default=300)

    runtime = config["RUNTIME"]
    _positive(runtime, "default_page_duration_s")
    _positive(runtime, "stale_after_s")
    _positive(runtime, "forced_refresh_s")
    _positive(runtime, "redraw_coalesce_ms")
    mode = runtime.get("message_mode", "poll")
    if mode not in ("poll", "event"):
        raise ConfigError("RUNTIME.message_mode must be poll or event")
    if mode == "event":
        _positive(runtime, "event_wait_ms", default=1000)

    buttons = config["BUTTONS"]
    for action, spec in buttons.items():
        if action not in BUTTON_ACTIONS:
            raise ConfigError("unsupported button action: {}".format(action))
        if "pin" not in spec:
            raise ConfigError("button {} is missing pin".format(action))

    pages = config["PAGE_PROFILES"][profile_name]
    if not pages:
        raise ConfigError("page profile must contain at least one page")
    seen = set()
    for page in pages:
        page_id = page.get("id")
        if not page_id or page_id in seen:
            raise ConfigError("page ids must be present and unique")
        seen.add(page_id)
        if "duration_s" in page:
            _positive(page, "duration_s")
        widgets = page.get("widgets")
        if not widgets:
            raise ConfigError("page {} has no widgets".format(page_id))
        for widget in widgets:
            _validate_widget(widget, display_type, page_id)
    return config


def _positive(mapping, key, default=None):
    try:
        value = float(mapping.get(key, default))
    except (KeyError, TypeError, ValueError):
        raise ConfigError("{} must be a positive number".format(key))
    if value <= 0:
        raise ConfigError("{} must be a positive number".format(key))


def _validate_widget(widget, display_type, page_id):
    widget_type = widget.get("type")
    supported = (
        "text",
        "value",
        "icon",
        "current_summary",
        "weather_alert",
        "hourly_table",
        "metadata",
        "server_status",
    )
    if widget_type not in supported:
        raise ConfigError(
            "page {} has unsupported widget {}".format(page_id, widget_type)
        )
    if display_type in ("ili9341", "pico_display_2"):
        for key in ("x", "y"):
            if key not in widget:
                raise ConfigError(
                    "TFT widget on page {} is missing {}".format(page_id, key)
                )
    elif display_type == "hd44780":
        for key in ("row", "col"):
            if key not in widget:
                raise ConfigError(
                    "LCD widget on page {} is missing {}".format(page_id, key)
                )
    if widget_type == "value" and not widget.get("path"):
        raise ConfigError("value widget on page {} needs path".format(page_id))
