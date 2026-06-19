from .character import CharacterDisplay
from .hd44780 import Hd44780, Hd44780Bus
from .ili9341 import Ili9341Display, Ili9341Surface
from .serial import SerialDisplay


def create_display(device):
    driver = device["driver"]
    try:
        if driver == "ili9341":
            surface = Ili9341Surface(
                device["pins"],
                rotation=device.get("rotation", 1),
                baudrate=device.get("baudrate", 40000000),
            )
            return Ili9341Display(surface)
        if driver == "hd44780":
            bus = Hd44780Bus(device["pins"])
            lcd = Hd44780(bus, device["columns"], device["rows"])
            return CharacterDisplay(
                lcd,
                device["columns"],
                device["rows"],
            )
    except Exception as exc:
        print("Display initialization failed:", exc)
        if device.get("serial_fallback", True):
            return SerialDisplay()
        raise
    raise ValueError("unsupported display driver: {}".format(driver))
