DEVICE = {
    "driver": "serial",
    "page_profile": "serial",
    # Set false for plain logs without terminal clear/home escape sequences.
    "ansi": True,
}

MQTT = {
    "host": "192.168.1.10",
    "port": 1883,
    "base_topic": "inkplate/weather-calendar",
    "client_id": "weather-cal-serial",
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

BUTTONS = {}

PAGE_PROFILES = {
    "serial": [
        {
            "id": "now",
            "duration_s": 10,
            "widgets": [
                {"type": "current_summary"},
                {
                    "type": "value",
                    "path": "wind",
                    "formatter": "wind",
                    "label": "Wind: ",
                },
                {
                    "type": "value",
                    "path": "rain",
                    "formatter": "rain",
                    "label": "Rain: ",
                },
                {"type": "metadata"},
            ],
        },
        {
            "id": "forecast",
            "widgets": [{"type": "hourly_table", "rows": 6}],
        },
        {
            "id": "system",
            "widgets": [
                {"type": "server_status"},
                {
                    "type": "value",
                    "path": "server.runtime.version",
                    "label": "Version: ",
                    "missing": "unknown",
                },
                {
                    "type": "value",
                    "path": "server.providers.forecast",
                    "label": "Provider: ",
                    "missing": "unknown",
                },
            ],
        },
    ]
}
