from .formatters import format_value, rain, temperature, wind
from .icons import icon_text, semantic_icon
from .topics import page_dependencies


ALERT_MARKER = "ALERT"


class PageRenderer:
    def __init__(self, display):
        self.display = display

    def render(self, page, state, stale=False, paused=False):
        self.display.begin(page.get("id", "page"))
        if stale:
            self.display.badge("STALE")
        if paused:
            self.display.badge("PAUSED", secondary=True)
        for widget in page.get("widgets", ()):
            self._render_widget(widget, state)
        self.display.end()

    def _render_widget(self, widget, state):
        widget_type = widget["type"]
        if widget_type == "text":
            self.display.text(widget, widget.get("text", ""))
        elif widget_type == "value":
            value = state.get(widget["path"], widget.get("missing"))
            text = format_value(value, widget.get("formatter", "text"))
            label = widget.get("label", "")
            self.display.text(widget, "{}{}".format(label, text))
        elif widget_type == "icon":
            identifier = state.get(widget.get("path", "current.icon"), "")
            self.display.icon(widget, semantic_icon(identifier))
        elif widget_type == "current_summary":
            current = state.data.get("current", {})
            pieces = [
                temperature(current.get("temperature")),
                icon_text(current.get("icon")),
            ]
            if current.get("alerts", {}).get("active", False):
                pieces.append(ALERT_MARKER)
            self.display.summary(widget, pieces)
        elif widget_type == "weather_alert":
            current = state.data.get("current", {})
            if current.get("alerts", {}).get("active", False):
                self.display.text(
                    widget,
                    widget.get("text", ALERT_MARKER),
                )
        elif widget_type == "hourly_table":
            self.display.hourly(widget, state.data.get("hourly", []))
        elif widget_type == "metadata":
            status = state.data.get("weather_status", {})
            text = _metadata_text(status, widget.get("width"))
            self.display.text(widget, text)
        elif widget_type == "server_status":
            server = state.data.get("server", {})
            producer = server.get("producer", {})
            text = "Server {}".format(producer.get("state", "unknown"))
            self.display.text(widget, text)


def pages_affected(pages, changed_topic):
    return {
        page["id"]
        for page in pages
        if changed_topic in page_dependencies(page)
    }


SOURCE_LABELS = {
    "openweathermap": "OWM",
    "openweathermapv3": "OWM v3",
    "openweathermapv4": "OWM v4",
}


def _metadata_text(status, width=None):
    source = str(status.get("source", ""))
    source = SOURCE_LABELS.get(source.lower(), source)
    generated_at = status.get("generated_at", "")
    clock = generated_at[11:16] if len(generated_at) >= 16 else ""
    if not width:
        return "{} {}".format(source, clock).strip()
    if not clock:
        return source[:width]
    source_width = max(0, width - len(clock) - 1)
    return "{} {}".format(source[:source_width], clock).strip()
