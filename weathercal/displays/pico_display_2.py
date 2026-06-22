from ..formatters import percent, temperature
from ..icons import BITMAPS, semantic_icon
from .base import Display


RGB = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "cyan": (0, 220, 255),
    "yellow": (255, 210, 0),
    "red": (255, 48, 48),
    "green": (40, 220, 100),
    "navy": (5, 18, 42),
    "panel": (14, 38, 68),
    "muted": (120, 160, 190),
}

INDICATORS = {
    "connecting": (0, 80, 255),
    "online": (0, 180, 40),
    "stale": (255, 120, 0),
    "paused": (180, 0, 255),
    "offline": (255, 0, 0),
    "error": (255, 0, 0),
}


class PicoDisplay2Display(Display):
    def __init__(self, graphics, led=None, font="bitmap8"):
        self.graphics = graphics
        self.led = led
        self.width, self.height = graphics.get_bounds()
        self.pens = {
            name: graphics.create_pen(*rgb) for name, rgb in RGB.items()
        }
        graphics.set_font(font)

    def begin(self, page_id):
        self._pen("navy")
        self.graphics.clear()

    def text(self, widget, value):
        if widget.get("card"):
            self._pen(widget.get("card_color", "panel"))
            self.graphics.rectangle(
                widget.get("card_x", widget.get("x", 0) - 6),
                widget.get("card_y", widget.get("y", 0) - 5),
                widget.get("card_width", self.width - widget.get("x", 0)),
                widget.get("card_height", 30),
            )
        self._pen(widget.get("color", "white"))
        self.graphics.text(
            str(value),
            widget.get("x", 0),
            widget.get("y", 0),
            widget.get("width", self.width - widget.get("x", 0)),
            widget.get("scale", 2),
        )

    def icon(self, widget, name):
        self._draw_icon(
            widget.get("x", 0),
            widget.get("y", 0),
            name,
            widget.get("scale", 2),
            widget.get("color", "yellow"),
        )

    def summary(self, widget, pieces):
        self.text(widget, " ".join(pieces))

    def hourly(self, widget, entries):
        x = widget.get("x", 0)
        y = widget.get("y", 0)
        row_height = widget.get("row_height", 44)
        rows = widget.get("rows", 4)
        for item in entries[:rows]:
            self._pen("panel")
            self.graphics.rectangle(
                x,
                y,
                widget.get("width", self.width - x),
                row_height - 4,
            )
            self._draw_icon(x + 6, y + 5, item.get("icon", ""), 1, "yellow")
            stamp = item.get("dt", "")
            hour = stamp[11:16] if len(stamp) >= 16 else "--:--"
            self._draw_text(hour, x + 28, y + 5, 2, "cyan", 82)
            self._draw_text(
                temperature(item.get("temperature")),
                x + 112,
                y + 5,
                2,
                "white",
                66,
            )
            self._draw_text(
                percent(item.get("rain_probability")),
                x + 180,
                y + 5,
                2,
                "cyan",
                68,
            )
            humidity = item.get("humidity")
            humidity_text = (
                "{}%".format(int(round(humidity)))
                if humidity is not None
                else "--"
            )
            self._draw_text(
                humidity_text,
                x + 250,
                y + 5,
                1,
                "muted",
                46,
            )
            y += row_height

    def badge(self, value, secondary=False):
        width = 66
        x = self.width - width - 4
        y = self.height - (25 if secondary else 48)
        self._pen("red")
        self.graphics.rectangle(x, y, width, 20)
        self._draw_text(value, x + 4, y + 2, 1, "white", width - 8)

    def indicator(self, state):
        if self.led:
            self.led.set_rgb(*INDICATORS.get(state, (0, 0, 0)))

    def end(self):
        self.graphics.update()

    def _draw_text(self, value, x, y, scale, color, width):
        self._pen(color)
        self.graphics.text(str(value), x, y, width, scale)

    def _draw_icon(self, x, y, name, scale, color):
        pattern = BITMAPS.get(semantic_icon(name), BITMAPS.get("cloud"))
        if not pattern:
            return
        self._pen(color)
        for row, bits in enumerate(pattern):
            for column, bit in enumerate(bits):
                if bit == "#":
                    self.graphics.rectangle(
                        x + column * scale,
                        y + row * scale,
                        scale,
                        scale,
                    )

    def _pen(self, name):
        self.graphics.set_pen(self.pens.get(name, self.pens["white"]))


def create_pico_display_2(device):
    try:
        from picographics import (
            DISPLAY_PICO_DISPLAY_2,
            PEN_P4,
            PicoGraphics,
        )
        from pimoroni import RGBLED
    except ImportError as exc:
        raise RuntimeError(
            "Pico Display Pack 2.0 requires Pimoroni MicroPython firmware "
            "with picographics and pimoroni modules"
        ) from exc

    graphics = PicoGraphics(
        display=DISPLAY_PICO_DISPLAY_2,
        pen_type=PEN_P4,
        rotate=device.get("rotation", 0),
    )
    graphics.set_backlight(device.get("backlight", 0.7))
    led = RGBLED(6, 7, 8)
    return PicoDisplay2Display(
        graphics,
        led=led,
        font=device.get("font", "bitmap8"),
    )
