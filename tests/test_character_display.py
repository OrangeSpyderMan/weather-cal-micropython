import unittest

from weathercal.displays.character import CharacterDisplay, _pad
from weathercal.pages import PageRenderer
from weathercal.state import WeatherState


class FakeLCD:
    def __init__(self):
        self.rows = {}
        self.row = 0
        self.glyphs = {}

    def clear(self):
        self.rows = {}

    def create_char(self, slot, rows):
        self.glyphs[slot] = rows

    def move_to(self, column, row):
        self.row = row

    def write(self, value):
        self.rows[self.row] = value


class CharacterDisplayTests(unittest.TestCase):
    def test_padding_does_not_depend_on_cpython_string_helpers(self):
        self.assertEqual(_pad("abc", 5, "left"), "abc  ")
        self.assertEqual(_pad("abc", 5, "right"), "  abc")
        self.assertEqual(_pad("abc", 6, "center"), " abc  ")

    def state(self):
        state = WeatherState()
        state.update(
            "current",
            {
                "temperature": {"value": 12, "unit": "°C"},
                "icon": "icon/rain.png",
            },
        )
        state.update(
            "hourly",
            [
                {
                    "dt": "2026-06-19T12:00:00Z",
                    "temperature": {"value": 13, "unit": "°C"},
                    "rain_probability": 80,
                },
                {
                    "dt": "2026-06-19T15:00:00Z",
                    "temperature": {"value": 15, "unit": "°C"},
                    "rain_probability": 20,
                },
            ],
        )
        state.update(
            "weather_status",
            {
                "source": "openweathermapv4",
                "generated_at": "2026-06-19T12:34:00Z",
            },
        )
        return state

    def test_1602_golden_buffer(self):
        lcd = FakeLCD()
        display = CharacterDisplay(lcd, 16, 2)
        renderer = PageRenderer(display)
        renderer.render(
            {
                "id": "now",
                "widgets": [
                    {
                        "type": "current_summary",
                        "row": 0,
                        "col": 0,
                        "width": 16,
                    },
                    {
                        "type": "text",
                        "text": "Weather Cal",
                        "row": 1,
                        "col": 0,
                        "width": 16,
                        "align": "center",
                    },
                ],
            },
            self.state(),
        )

        self.assertEqual(lcd.rows[0], "12C RAIN        ")
        self.assertEqual(lcd.rows[1], "  Weather Cal   ")

    def test_2004_hourly_golden_buffer(self):
        lcd = FakeLCD()
        display = CharacterDisplay(lcd, 20, 4)
        renderer = PageRenderer(display)
        renderer.render(
            {
                "id": "forecast",
                "widgets": [
                    {
                        "type": "hourly_table",
                        "row": 0,
                        "col": 0,
                        "rows": 4,
                    }
                ],
            },
            self.state(),
        )

        self.assertEqual(lcd.rows[0], "12:00 13C 80%       ")
        self.assertEqual(lcd.rows[1], "15:00 15C 20%       ")
        self.assertEqual(lcd.rows[2], "                    ")
        self.assertEqual(lcd.rows[3], "                    ")

    def test_2004_metadata_abbreviates_source_and_keeps_time(self):
        lcd = FakeLCD()
        display = CharacterDisplay(lcd, 20, 4)
        renderer = PageRenderer(display)
        renderer.render(
            {
                "id": "now",
                "widgets": [
                    {
                        "type": "metadata",
                        "row": 3,
                        "col": 0,
                        "width": 20,
                        "align": "center",
                    }
                ],
            },
            self.state(),
        )

        self.assertEqual(lcd.rows[3], "    OWM v4 12:34    ")
