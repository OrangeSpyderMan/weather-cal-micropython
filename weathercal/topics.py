TOPIC_SUFFIXES = {
    "current": "current",
    "hourly": "hourly",
    "weather_status": "status",
    "generated_at": "generated_at",
    "rain": "current/rain",
    "wind": "current/wind",
    "server_status": "server/status",
}

WIDGET_DEPENDENCIES = {
    "text": (),
    "value": (),
    "icon": ("current",),
    "current_summary": ("current",),
    "weather_alert": ("current",),
    "hourly_table": ("hourly",),
    "metadata": ("weather_status",),
    "server_status": ("server_status",),
}


def widget_dependencies(widget):
    dependencies = set(WIDGET_DEPENDENCIES.get(widget.get("type"), ()))
    path = widget.get("path", "")
    if path:
        root = path.split(".", 1)[0]
        aliases = {
            "current": "current",
            "hourly": "hourly",
            "weather_status": "weather_status",
            "generated_at": "generated_at",
            "rain": "rain",
            "wind": "wind",
            "server": "server_status",
        }
        if root in aliases:
            dependencies.add(aliases[root])
    return dependencies


def page_dependencies(page):
    result = set()
    for widget in page.get("widgets", ()):
        result.update(widget_dependencies(widget))
    return result


def infer_topics(base_topic, pages):
    dependencies = set()
    for page in pages:
        dependencies.update(page_dependencies(page))
    return {
        name: "{}/{}".format(base_topic.rstrip("/"), TOPIC_SUFFIXES[name])
        for name in sorted(dependencies)
    }
