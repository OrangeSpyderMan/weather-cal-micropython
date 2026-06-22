import sys
import types
import unittest
from unittest import mock

from weathercal.displays.pico_display_2 import (
    PicoDisplay2Display,
    create_pico_display_2,
)


class FakeGraphics:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.commands = []
        self.backlight = None
        self.font = None
        FakeGraphics.instances.append(self)

    def get_bounds(self):
        return (320, 240)

    def create_pen(self, red, green, blue):
        return (red, green, blue)

    def set_font(self, font):
        self.font = font

    def set_backlight(self, value):
        self.backlight = value

    def set_pen(self, pen):
        self.commands.append(("pen", pen))

    def clear(self):
        self.commands.append(("clear",))

    def rectangle(self, x, y, width, height):
        self.commands.append(("rectangle", x, y, width, height))

    def text(self, value, x, y, width, scale):
        self.commands.append(("text", value, x, y, width, scale))

    def update(self):
        self.commands.append(("update",))


class FakeLED:
    instances = []

    def __init__(self, red, green, blue):
        self.pins = (red, green, blue)
        self.values = []
        FakeLED.instances.append(self)

    def set_rgb(self, red, green, blue):
        self.values.append((red, green, blue))


class PicoDisplay2Tests(unittest.TestCase):
    def setUp(self):
        FakeGraphics.instances = []
        FakeLED.instances = []

    def test_factory_uses_p4_rotation_backlight_font_and_rgb_led(self):
        picographics = types.ModuleType("picographics")
        picographics.PicoGraphics = FakeGraphics
        picographics.DISPLAY_PICO_DISPLAY_2 = "display-2"
        picographics.PEN_P4 = "p4"
        pimoroni = types.ModuleType("pimoroni")
        pimoroni.RGBLED = FakeLED

        with mock.patch.dict(
            sys.modules,
            {"picographics": picographics, "pimoroni": pimoroni},
        ):
            display = create_pico_display_2(
                {
                    "rotation": 180,
                    "backlight": 0.6,
                    "font": "bitmap8",
                }
            )

        graphics = FakeGraphics.instances[0]
        self.assertIsInstance(display, PicoDisplay2Display)
        self.assertEqual(
            graphics.kwargs,
            {"display": "display-2", "pen_type": "p4", "rotate": 180},
        )
        self.assertEqual(graphics.backlight, 0.6)
        self.assertEqual(graphics.font, "bitmap8")
        self.assertEqual(FakeLED.instances[0].pins, (6, 7, 8))

    def test_renders_cards_icons_forecast_badges_and_updates(self):
        graphics = FakeGraphics()
        led = FakeLED(6, 7, 8)
        display = PicoDisplay2Display(graphics, led=led)

        display.begin("forecast")
        display.text(
            {
                "x": 12,
                "y": 10,
                "scale": 2,
                "card": True,
                "card_width": 100,
                "card_height": 30,
            },
            "FORECAST",
        )
        display.icon({"x": 2, "y": 3, "scale": 1}, "clear")
        display.hourly(
            {"x": 8, "y": 48, "rows": 1, "row_height": 47},
            [
                {
                    "dt": "2026-06-22T12:00:00+02:00",
                    "icon": "icon/day/partly-clear.png",
                    "temperature": {"value": 27, "unit": "C"},
                    "rain_probability": 20,
                    "humidity": 42,
                }
            ],
        )
        display.badge("STALE")
        display.end()

        self.assertIn(("clear",), graphics.commands)
        self.assertIn(("text", "FORECAST", 12, 10, 308, 2), graphics.commands)
        self.assertIn(("text", "12:00", 36, 53, 82, 2), graphics.commands)
        self.assertIn(("text", "27C", 120, 53, 66, 2), graphics.commands)
        self.assertIn(("text", "20%", 188, 53, 68, 2), graphics.commands)
        self.assertIn(("text", "42%", 258, 53, 46, 1), graphics.commands)
        self.assertEqual(graphics.commands[-1], ("update",))
        self.assertGreater(
            len([item for item in graphics.commands if item[0] == "rectangle"]),
            10,
        )

    def test_indicator_maps_operational_states_to_rgb(self):
        graphics = FakeGraphics()
        led = FakeLED(6, 7, 8)
        display = PicoDisplay2Display(graphics, led=led)

        for state in ("connecting", "online", "stale", "paused", "error"):
            display.indicator(state)

        self.assertEqual(
            led.values,
            [
                (0, 80, 255),
                (0, 180, 40),
                (255, 120, 0),
                (180, 0, 255),
                (255, 0, 0),
            ],
        )

    def test_missing_pimoroni_modules_reports_firmware_requirement(self):
        with mock.patch.dict(
            sys.modules,
            {"picographics": None, "pimoroni": None},
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "requires Pimoroni MicroPython firmware",
            ):
                create_pico_display_2({})


if __name__ == "__main__":
    unittest.main()
