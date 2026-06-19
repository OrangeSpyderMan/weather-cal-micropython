try:
    from machine import Pin, SPI
except ImportError:
    Pin = None
    SPI = None

from ..compat import sleep_ms
from ..formatters import percent, temperature
from ..icons import BITMAPS
from .base import Display
from .font5x7 import glyph


BLACK = 0x0000
WHITE = 0xFFFF
CYAN = 0x07FF
YELLOW = 0xFFE0
RED = 0xF800
GREEN = 0x07E0
NAVY = 0x0010


class Ili9341Surface:
    def __init__(self, pins, rotation=1, baudrate=40000000):
        if Pin is None or SPI is None:
            raise RuntimeError("machine SPI support is unavailable")
        self.cs = Pin(pins["cs"], Pin.OUT, value=1)
        self.dc = Pin(pins["dc"], Pin.OUT)
        self.reset = Pin(pins["reset"], Pin.OUT, value=1)
        self.spi = SPI(
            pins.get("spi_id", 0),
            baudrate=baudrate,
            sck=Pin(pins["sck"]),
            mosi=Pin(pins["mosi"]),
            miso=Pin(pins["miso"]) if pins.get("miso") is not None else None,
        )
        self.width = 320 if rotation % 2 else 240
        self.height = 240 if rotation % 2 else 320
        self._reset()
        for command, data in (
            (0x01, None),
            (0x28, None),
            (0x3A, b"\x55"),
            (0x36, bytes((0x28 if rotation == 1 else 0xE8,))),
            (0x11, None),
            (0x29, None),
        ):
            self.command(command, data)
            sleep_ms(10)

    def command(self, command, data=None):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes((command,)))
        if data:
            self.dc.value(1)
            self.spi.write(data)
        self.cs.value(1)

    def fill_rect(self, x, y, width, height, color):
        if width <= 0 or height <= 0:
            return
        self.command(0x2A, _coords(x, x + width - 1))
        self.command(0x2B, _coords(y, y + height - 1))
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(b"\x2c")
        self.dc.value(1)
        pixel = bytes((color >> 8, color & 0xFF))
        block = pixel * min(width * height, 128)
        remaining = width * height
        while remaining:
            count = min(remaining, 128)
            self.spi.write(block[: count * 2])
            remaining -= count
        self.cs.value(1)

    def draw_text(self, x, y, value, color=WHITE, scale=2):
        cursor = x
        for character in str(value):
            pattern = glyph(character)
            for row, bits in enumerate(pattern):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        self.fill_rect(
                            cursor + column * scale,
                            y + row * scale,
                            scale,
                            scale,
                            color,
                        )
            cursor += 6 * scale

    def draw_icon(self, x, y, name, color=YELLOW, scale=2):
        pattern = BITMAPS.get(name, BITMAPS.get("cloud"))
        if not pattern:
            return
        for row, bits in enumerate(pattern):
            for column, bit in enumerate(bits):
                if bit == "#":
                    self.fill_rect(
                        x + column * scale,
                        y + row * scale,
                        scale,
                        scale,
                        color,
                    )

    def clear(self, color=BLACK):
        self.fill_rect(0, 0, self.width, self.height, color)

    def _reset(self):
        self.reset.value(0)
        sleep_ms(10)
        self.reset.value(1)
        sleep_ms(120)


class Ili9341Display(Display):
    COLORS = {
        "white": WHITE,
        "cyan": CYAN,
        "yellow": YELLOW,
        "red": RED,
        "green": GREEN,
    }

    def __init__(self, surface):
        self.surface = surface

    def begin(self, page_id):
        self.surface.clear(NAVY)

    def text(self, widget, value):
        self.surface.draw_text(
            widget.get("x", 0),
            widget.get("y", 0),
            value,
            self.COLORS.get(widget.get("color", "white"), WHITE),
            widget.get("scale", 2),
        )

    def icon(self, widget, name):
        self.surface.draw_icon(
            widget.get("x", 0),
            widget.get("y", 0),
            name,
            self.COLORS.get(widget.get("color", "yellow"), YELLOW),
            widget.get("scale", 2),
        )

    def summary(self, widget, pieces):
        self.text(widget, " ".join(pieces))

    def hourly(self, widget, entries):
        y = widget.get("y", 0)
        row_height = widget.get("row_height", 30)
        scale = widget.get("scale", 2)
        for item in entries[: widget.get("rows", 3)]:
            stamp = item.get("dt", "")
            hour = stamp[11:16] if len(stamp) >= 16 else "--:--"
            text = "{}  {}  {}".format(
                hour,
                temperature(item.get("temperature")),
                percent(item.get("rain_probability")),
            )
            self.surface.draw_text(
                widget.get("x", 0),
                y,
                text,
                WHITE,
                scale,
            )
            y += row_height

    def badge(self, value, secondary=False):
        y = 222 if secondary else 204
        self.surface.fill_rect(250, y, 70, 18, RED)
        self.surface.draw_text(254, y + 3, value, WHITE, 1)

    def end(self):
        pass


def _coords(start, end):
    return bytes((start >> 8, start & 0xFF, end >> 8, end & 0xFF))
