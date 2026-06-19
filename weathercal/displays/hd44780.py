try:
    from machine import Pin
except ImportError:
    Pin = None

from ..compat import sleep_ms


class Hd44780Bus:
    def __init__(self, pins):
        if Pin is None:
            raise RuntimeError("machine.Pin is unavailable")
        self.rs = Pin(pins["rs"], Pin.OUT)
        self.enable = Pin(pins["enable"], Pin.OUT)
        self.data = [Pin(pins[name], Pin.OUT) for name in ("d4", "d5", "d6", "d7")]
        self.backlight = (
            Pin(pins["backlight"], Pin.OUT)
            if pins.get("backlight") is not None
            else None
        )
        if self.backlight:
            self.backlight.value(1)
        sleep_ms(50)
        for command in (0x03, 0x03, 0x03, 0x02):
            self._nibble(command)
            sleep_ms(5)

    def send(self, value, data=False):
        self.rs.value(1 if data else 0)
        self._nibble(value >> 4)
        self._nibble(value)
        sleep_ms(1)

    def _nibble(self, value):
        for index, pin in enumerate(self.data):
            pin.value((value >> index) & 1)
        self.enable.value(1)
        sleep_ms(1)
        self.enable.value(0)


class Hd44780:
    OFFSETS = (0x00, 0x40, 0x14, 0x54)

    def __init__(self, bus, columns, rows):
        self.bus = bus
        self.columns = columns
        self.rows = rows
        self.bus.send(0x28)
        self.bus.send(0x0C)
        self.bus.send(0x06)
        self.clear()

    def clear(self):
        self.bus.send(0x01)
        sleep_ms(2)

    def move_to(self, column, row):
        self.bus.send(0x80 | (self.OFFSETS[row] + column))

    def write(self, value):
        for character in value:
            self.bus.send(ord(character), data=True)

    def create_char(self, slot, rows):
        self.bus.send(0x40 | ((slot & 0x07) << 3))
        for row in rows:
            self.bus.send(row, data=True)
