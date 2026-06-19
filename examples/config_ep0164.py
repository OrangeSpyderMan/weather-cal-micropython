DEVICE = {
    "driver": "ili9341",
    "page_profile": "ep0164",
    "rotation": 1,
    "baudrate": 40000000,
    "serial_fallback": True,
    "pins": {
        "spi_id": 0,
        "sck": 6,
        "mosi": 7,
        "miso": 4,
        "cs": 13,
        "reset": 14,
        "dc": 15,
    },
}

MQTT = {
    "host": "192.168.1.10",
    "port": 1883,
    "base_topic": "inkplate/weather-calendar",
    "client_id": "weather-cal-ep0164",
    "keepalive_s": 60,
    "reconnect_min_s": 2,
    "reconnect_max_s": 60,
}

RUNTIME = {
    "default_page_duration_s": 8,
    "redraw_coalesce_ms": 250,
    "forced_refresh_s": 300,
    "stale_after_s": 14400,
    "button_debounce_ms": 180,
    "loop_sleep_ms": 50,
}

BUTTONS = {
    "previous": {"pin": 18, "active_low": True},
    "next": {"pin": 19, "active_low": True},
    "home": {"pin": 20, "active_low": True},
    "pause": {"pin": 21, "active_low": True},
}

PAGE_PROFILES = {
    "ep0164": [
        {
            "id": "now",
            "duration_s": 10,
            "widgets": [
                {
                    "type": "text",
                    "text": "WEATHER CAL",
                    "x": 12,
                    "y": 10,
                    "scale": 3,
                    "color": "cyan",
                },
                {
                    "type": "icon",
                    "path": "current.icon",
                    "x": 20,
                    "y": 62,
                    "scale": 5,
                },
                {
                    "type": "value",
                    "path": "current.temperature",
                    "formatter": "temperature",
                    "x": 120,
                    "y": 70,
                    "scale": 5,
                    "color": "white",
                },
                {
                    "type": "value",
                    "path": "wind",
                    "formatter": "wind",
                    "x": 16,
                    "y": 165,
                    "scale": 2,
                },
                {
                    "type": "value",
                    "path": "rain",
                    "formatter": "rain",
                    "label": "RAIN ",
                    "x": 16,
                    "y": 195,
                    "scale": 2,
                },
            ],
        },
        {
            "id": "forecast",
            "duration_s": 9,
            "widgets": [
                {
                    "type": "text",
                    "text": "NEXT HOURS",
                    "x": 12,
                    "y": 10,
                    "scale": 3,
                    "color": "cyan",
                },
                {
                    "type": "hourly_table",
                    "x": 16,
                    "y": 62,
                    "rows": 5,
                    "row_height": 32,
                    "scale": 2,
                },
            ],
        },
        {
            "id": "system",
            "widgets": [
                {
                    "type": "text",
                    "text": "SYSTEM",
                    "x": 12,
                    "y": 10,
                    "scale": 3,
                    "color": "cyan",
                },
                {"type": "metadata", "x": 16, "y": 72, "scale": 2},
                {"type": "server_status", "x": 16, "y": 110, "scale": 2},
                {
                    "type": "value",
                    "path": "server.runtime.version",
                    "label": "VER ",
                    "x": 16,
                    "y": 148,
                    "scale": 2,
                    "missing": "unknown",
                },
            ],
        },
    ]
}
