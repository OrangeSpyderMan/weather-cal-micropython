from ..formatters import percent, temperature
from ..icons import icon_text
from .base import Display


class SerialDisplay(Display):
    def __init__(self, ansi=True, output=print):
        self.ansi = ansi
        self.output = output
        self.lines = []
        self.badges = []
        self.page_id = ""

    def begin(self, page_id):
        self.page_id = page_id
        self.lines = []
        self.badges = []

    def text(self, widget, value):
        value = str(value).strip()
        if value:
            self.lines.append(value)

    def icon(self, widget, name):
        self.lines.append("Weather: {}".format(icon_text(name)))

    def summary(self, widget, pieces):
        self.lines.append("Now: {}".format(" ".join(pieces)))

    def hourly(self, widget, entries):
        self.lines.append("Forecast:")
        for item in entries[: widget.get("rows", len(entries))]:
            stamp = item.get("dt", "")
            hour = stamp[11:16] if len(stamp) >= 16 else "--:--"
            self.lines.append(
                "  {}  {}  rain {}".format(
                    hour,
                    temperature(item.get("temperature")),
                    percent(item.get("rain_probability")),
                )
            )

    def badge(self, value, secondary=False):
        self.badges.append(value)

    def end(self):
        if self.ansi:
            self.output("\x1b[2J\x1b[H", end="")
        title = "Weather Cal - {}".format(self.page_id)
        if self.badges:
            title += " [{}]".format(", ".join(self.badges))
        self.output(title)
        self.output("=" * len(title))
        for line in self.lines:
            self.output(line)
