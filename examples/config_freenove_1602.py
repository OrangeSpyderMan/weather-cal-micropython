DEVICE = {
    "driver": "hd44780",
    "transport": "pcf8574",
    "page_profile": "lcd1602",
    "columns": 16,
    "rows": 2,
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
    "client_id": "weather-cal-lcd1602",
    "keepalive_s": 60,
    "reconnect_min_s": 2,
    "reconnect_max_s": 60,
}

RUNTIME = {
    "default_page_duration_s": 6,
    "redraw_coalesce_ms": 250,
    "forced_refresh_s": 180,
    "stale_after_s": 14400,
    "button_debounce_ms": 180,
    "loop_sleep_ms": 50,
}

BUTTONS = {}

PAGE_PROFILES = {
    "lcd1602": [
        {
            "id": "now",
            "widgets": [
                {
                    "type": "current_summary",
                    "row": 0,
                    "col": 0,
                    "width": 16,
                },
                {
                    "type": "value",
                    "path": "wind",
                    "formatter": "wind",
                    "row": 1,
                    "col": 0,
                    "width": 16,
                },
            ],
        },
        {
            "id": "rain",
            "widgets": [
                {
                    "type": "text",
                    "text": "Rain now",
                    "row": 0,
                    "col": 0,
                    "width": 16,
                    "align": "center",
                },
                {
                    "type": "value",
                    "path": "rain",
                    "formatter": "rain",
                    "row": 1,
                    "col": 0,
                    "width": 16,
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
                    "rows": 2,
                }
            ],
        },
    ]
}
