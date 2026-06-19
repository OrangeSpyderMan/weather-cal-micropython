try:
    import gc
except ImportError:
    gc = None

from . import __version__
from .compat import json, ticks_diff
from .timeutil import age_seconds


STATUS_SCHEMA_VERSION = "1.0"


def diagnostic_topic(mqtt):
    settings = mqtt.get("diagnostics", {})
    return settings.get(
        "topic",
        "{}/diagnostics".format(mqtt["base_topic"].rstrip("/")),
    )


def status_topic(mqtt):
    settings = mqtt.get("diagnostics", {})
    return settings.get(
        "status_topic",
        "{}/clients/{}/status".format(
            mqtt["base_topic"].rstrip("/"),
            mqtt["client_id"],
        ),
    )


def offline_payload(config):
    return json.dumps(
        {
            "schema_version": STATUS_SCHEMA_VERSION,
            "client_id": config["MQTT"]["client_id"],
            "state": "offline",
        }
    )


def status_payload(app, now_ms, state="online"):
    generated_at = app.state.generated_at()
    age = age_seconds(generated_at)
    runtime = app.config["RUNTIME"]
    payload = {
        "schema_version": STATUS_SCHEMA_VERSION,
        "client_id": app.config["MQTT"]["client_id"],
        "state": state,
        "version": __version__,
        "uptime_s": max(0, ticks_diff(now_ms, app.started_ms) // 1000),
        "mqtt_connected": bool(app.connected),
        "display": _display_status(app.config["DEVICE"]),
        "active_page": app.scheduler.page["id"],
        "rotation_paused": bool(app.scheduler.paused),
        "weather_generated_at": generated_at,
        "weather_age_s": int(age) if age is not None else None,
        "weather_stale": age is None or age > runtime["stale_after_s"],
        "free_memory": _free_memory(),
        "wifi": _wifi_status(app.network),
        "last_error": app.last_error,
    }
    return json.dumps(payload)


def diagnostic_message(client_id, level, message):
    return "{} [{}] {}".format(client_id, level, message)


def _display_status(device):
    result = {
        "driver": device["driver"],
        "page_profile": device["page_profile"],
    }
    for name in ("columns", "rows", "rotation"):
        if name in device:
            result[name] = device[name]
    return result


def _free_memory():
    if gc is None or not hasattr(gc, "mem_free"):
        return None
    try:
        return gc.mem_free()
    except Exception:
        return None


def _wifi_status(network):
    if network is None:
        return {"connected": False}
    result = {"connected": bool(network.connected())}
    for name in ("ip_address", "rssi"):
        method = getattr(network, name, None)
        if method:
            try:
                result[name] = method()
            except Exception:
                result[name] = None
    return result
