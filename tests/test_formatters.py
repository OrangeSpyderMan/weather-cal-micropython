import unittest

from weathercal.formatters import (
    age_label,
    clock,
    percent,
    rain,
    temperature,
    wind,
)
from weathercal.icons import semantic_icon


class FormatterTests(unittest.TestCase):
    def test_weather_measurements(self):
        self.assertEqual(temperature({"value": 11, "unit": "°C"}), "11C")
        self.assertEqual(percent(85), "85%")
        self.assertEqual(
            wind(
                {
                    "value": 4.2,
                    "unit": "m/s",
                    "direction_cardinal": "WSW",
                }
            ),
            "15.1km/h WSW",
        )
        self.assertEqual(
            rain({"value": 0.4, "rate_unit": "mm/h"}),
            "0.4mm/h",
        )

    def test_time_and_age_formatting(self):
        self.assertEqual(clock("2026-06-19T12:34:00+00:00"), "12:34")
        self.assertEqual(age_label(59), "59s")
        self.assertEqual(age_label(120), "2m")
        self.assertEqual(age_label(7200), "2h")

    def test_icon_mapping(self):
        self.assertEqual(semantic_icon("icon/day/clear.png"), "clear")
        self.assertEqual(semantic_icon("icon/thunder-showers.png"), "storm")
        self.assertEqual(semantic_icon(""), "weather")
