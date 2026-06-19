try:
    from machine import I2C, Pin
except ImportError:
    I2C = None
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


class Pcf8574Bus:
    RS = 0x01
    ENABLE = 0x04
    BACKLIGHT = 0x08
    COMMON_ADDRESSES = (0x27, 0x3F)

    def __init__(self, config, i2c=None):
        if i2c is None:
            if I2C is None or Pin is None:
                raise RuntimeError("machine.I2C is unavailable")
            i2c = I2C(
                config.get("i2c_id", 0),
                sda=Pin(config["sda"]),
                scl=Pin(config["scl"]),
                freq=config.get("frequency", 100000),
            )
        self.i2c = i2c
        self.backlight = (
            self.BACKLIGHT if config.get("backlight", True) else 0
        )
        self.address = self._address(config.get("address"))
        sleep_ms(50)
        for command in (0x03, 0x03, 0x03, 0x02):
            self._nibble(command, data=False)
            sleep_ms(5)

    def send(self, value, data=False):
        self._nibble(value >> 4, data)
        self._nibble(value, data)
        sleep_ms(1)

    def set_backlight(self, enabled):
        self.backlight = self.BACKLIGHT if enabled else 0
        self._write(0)

    def _address(self, configured):
        detected = self.i2c.scan()
        if configured is not None:
            if configured not in detected:
                raise OSError(
                    "PCF8574 address 0x{:02x} not found; detected {}".format(
                        configured,
                        _addresses(detected),
                    )
                )
            return configured
        common = [
            address
            for address in detected
            if address in self.COMMON_ADDRESSES
        ]
        if len(common) == 1:
            return common[0]
        if not common:
            raise OSError(
                "no PCF8574 LCD found at 0x27 or 0x3f; detected {}".format(
                    _addresses(detected)
                )
            )
        raise OSError(
            "multiple PCF8574 LCDs detected {}; configure address".format(
                _addresses(common)
            )
        )

    def _nibble(self, value, data):
        output = ((value & 0x0F) << 4) | self.backlight
        if data:
            output |= self.RS
        self._write(output)
        self._write(output | self.ENABLE)
        sleep_ms(1)
        self._write(output)

    def _write(self, value):
        self.i2c.writeto(self.address, bytes((value,)))


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


def _addresses(values):
    return ", ".join("0x{:02x}".format(value) for value in values) or "none"
