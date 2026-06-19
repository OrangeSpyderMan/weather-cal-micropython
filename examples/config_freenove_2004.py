DEVICE = {
    "driver": "hd44780",
    "transport": "pcf8574",
    "page_profile": "lcd2004",
    "columns": 20,
    "rows": 4,
    "serial_fallback": True,
    "i2c": {
        "i2c_id": 0,
        "sda": 0,
        "scl": 1,
        "frequency": 100000,
        # None scans common backpack addresses 0x27 and 0x3f.
        "address": None,
        "backlight": True,
    },
}

MQTT = {
    "host": "192.168.1.10",
    "port": 1883,
    "base_topic": "inkplate/weather-calendar",
    "client_id": "weather-cal-lcd2004",
    "keepalive_s": 60,
    "reconnect_min_s": 2,
    "reconnect_max_s": 60,
}

RUNTIME = {
    "default_page_duration_s": 8,
    "redraw_coalesce_ms": 250,
    "forced_refresh_s": 180,
    "stale_after_s": 14400,
    "button_debounce_ms": 180,
    "loop_sleep_ms": 50,
}

BUTTONS = {}

PAGE_PROFILES = {
    "lcd2004": [
        {
            "id": "now",
            "widgets": [
                {
                    "type": "current_summary",
                    "row": 0,
                    "col": 0,
                    "width": 20,
                    "align": "center",
                },
                {
                    "type": "value",
                    "path": "wind",
                    "formatter": "wind",
                    "label": "Wind ",
                    "row": 1,
                    "col": 0,
                    "width": 20,
                },
                {
                    "type": "value",
                    "path": "rain",
                    "formatter": "rain",
                    "label": "Rain ",
                    "row": 2,
                    "col": 0,
                    "width": 20,
                },
                {
                    "type": "metadata",
                    "row": 3,
                    "col": 0,
                    "width": 20,
                    "align": "center",
                },
            ],
        },
        {
            "id": "forecast",
            "widgets": [
                {
                    "type": "hourly_table",
                    "row": 0,
                    "col": 0,
                    "rows": 4,
                }
            ],
        },
        {
            "id": "system",
            "widgets": [
                {
                    "type": "server_status",
                    "row": 0,
                    "col": 0,
                    "width": 20,
                },
                {
                    "type": "value",
                    "path": "server.runtime.version",
                    "label": "Ver ",
                    "row": 1,
                    "col": 0,
                    "width": 20,
                    "missing": "unknown",
                },
                {
                    "type": "value",
                    "path": "server.providers.forecast",
                    "label": "Wx ",
                    "row": 2,
                    "col": 0,
                    "width": 20,
                    "missing": "unknown",
                },
                {
                    "type": "metadata",
                    "row": 3,
                    "col": 0,
                    "width": 20,
                },
            ],
        },
    ]
}
