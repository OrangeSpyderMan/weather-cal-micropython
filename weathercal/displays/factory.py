from .character import CharacterDisplay
from .hd44780 import Hd44780, Hd44780Bus, Pcf8574Bus
from .ili9341 import Ili9341Display, Ili9341Surface
from .serial import SerialDisplay


def create_display(device):
    driver = device["driver"]
    if driver == "serial":
        return SerialDisplay(ansi=device.get("ansi", True))
    try:
        if driver == "ili9341":
            surface = Ili9341Surface(
                device["pins"],
                rotation=device.get("rotation", 1),
                baudrate=device.get("baudrate", 40000000),
            )
            return Ili9341Display(surface)
        if driver == "hd44780":
            transport = device.get("transport", "gpio")
            if transport == "pcf8574":
                bus = Pcf8574Bus(device["i2c"])
            elif transport == "gpio":
                bus = Hd44780Bus(device["pins"])
            else:
                raise ValueError(
                    "unsupported HD44780 transport: {}".format(transport)
                )
            lcd = Hd44780(bus, device["columns"], device["rows"])
            return CharacterDisplay(
                lcd,
                device["columns"],
                device["rows"],
            )
    except Exception as exc:
        print("Display initialization failed:", exc)
        if device.get("serial_fallback", True):
            return SerialDisplay(ansi=device.get("serial_ansi", True))
        raise
    raise ValueError("unsupported display driver: {}".format(driver))
