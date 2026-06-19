import unittest

from weathercal.displays.ili9341 import (
    Ili9341Display,
    WHITE,
    YELLOW,
    rotation_geometry,
)
from weathercal.pages import PageRenderer
from weathercal.state import WeatherState


class RecordingSurface:
    def __init__(self):
        self.commands = []

    def clear(self, color):
        self.commands.append(("clear", color))

    def draw_text(self, x, y, value, color, scale):
        self.commands.append(("text", x, y, value, color, scale))

    def draw_icon(self, x, y, name, color, scale):
        self.commands.append(("icon", x, y, name, color, scale))

    def fill_rect(self, x, y, width, height, color):
        self.commands.append(("rect", x, y, width, height, color))


class Ili9341DisplayTests(unittest.TestCase):
    def test_all_four_rotations_have_expected_geometry_and_madctl(self):
        self.assertEqual(rotation_geometry(0), (240, 320, 0x48))
        self.assertEqual(rotation_geometry(1), (320, 240, 0x28))
        self.assertEqual(rotation_geometry(2), (240, 320, 0x88))
        self.assertEqual(rotation_geometry(3), (320, 240, 0xE8))

        with self.assertRaisesRegex(ValueError, "0, 1, 2, or 3"):
            rotation_geometry(4)

    def test_drawing_snapshot_and_icon_mapping(self):
        surface = RecordingSurface()
        display = Ili9341Display(surface)
        state = WeatherState()
        state.update(
            "current",
            {
                "temperature": {"value": 10, "unit": "°C"},
                "icon": "icon/day/clear.png",
            },
        )
        PageRenderer(display).render(
            {
                "id": "now",
                "widgets": [
                    {
                        "type": "text",
                        "text": "NOW",
                        "x": 4,
                        "y": 6,
                        "scale": 3,
                    },
                    {
                        "type": "icon",
                        "path": "current.icon",
                        "x": 10,
                        "y": 30,
                        "scale": 2,
                    },
                ],
            },
            state,
        )

        self.assertEqual(
            surface.commands,
            [
                ("clear", 16),
                ("text", 4, 6, "NOW", WHITE, 3),
                ("icon", 10, 30, "clear", YELLOW, 2),
            ],
        )

    def test_stale_and_paused_badges_are_rendered(self):
        surface = RecordingSurface()
        surface.width = 320
        surface.height = 240
        display = Ili9341Display(surface)
        PageRenderer(display).render(
            {
                "id": "status",
                "widgets": [
                    {"type": "text", "text": "WX", "x": 0, "y": 0}
                ],
            },
            WeatherState(),
            stale=True,
            paused=True,
        )

        self.assertIn(("rect", 250, 204, 70, 18, 63488), surface.commands)
        self.assertIn(("rect", 250, 222, 70, 18, 63488), surface.commands)
