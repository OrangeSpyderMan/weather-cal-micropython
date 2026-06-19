import unittest

from weathercal.displays.factory import create_display
from weathercal.displays.serial import SerialDisplay
from weathercal.pages import PageRenderer
from weathercal.state import WeatherState


class SerialDisplayTests(unittest.TestCase):
    def test_plain_serial_page_is_human_readable(self):
        output = []
        display = SerialDisplay(
            ansi=False,
            output=lambda value, **kwargs: output.append(value),
        )
        state = WeatherState()
        state.update(
            "current",
            {
                "temperature": {"value": 12, "unit": "C"},
                "icon": "icon/rain.png",
            },
        )
        state.update(
            "wind",
            {"value": 18, "unit": "kmh", "direction_cardinal": "W"},
        )
        PageRenderer(display).render(
            {
                "id": "now",
                "widgets": [
                    {"type": "current_summary"},
                    {
                        "type": "value",
                        "path": "wind",
                        "formatter": "wind",
                        "label": "Wind: ",
                    },
                ],
            },
            state,
            stale=True,
        )

        self.assertEqual(output[0], "Weather Cal - now [STALE]")
        self.assertIn("Now: 12C RAIN", output)
        self.assertIn("Wind: 18km/h W", output)

    def test_ansi_mode_clears_terminal(self):
        output = []
        display = SerialDisplay(
            ansi=True,
            output=lambda value, **kwargs: output.append(value),
        )
        display.begin("status")
        display.text({}, "Connected")
        display.end()

        self.assertEqual(output[0], "\x1b[2J\x1b[H")

    def test_factory_supports_serial_as_primary_driver(self):
        display = create_display({"driver": "serial", "ansi": False})

        self.assertIsInstance(display, SerialDisplay)
        self.assertFalse(display.ansi)
