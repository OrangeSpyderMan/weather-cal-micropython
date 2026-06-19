from .formatters import format_value, rain, temperature, wind
from .icons import icon_text, semantic_icon
from .topics import page_dependencies


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
            self.display.summary(widget, pieces)
        elif widget_type == "hourly_table":
            self.display.hourly(widget, state.data.get("hourly", []))
        elif widget_type == "metadata":
            status = state.data.get("weather_status", {})
            text = "{} {}".format(
                status.get("source", ""),
                status.get("generated_at", "")[11:16],
            ).strip()
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
