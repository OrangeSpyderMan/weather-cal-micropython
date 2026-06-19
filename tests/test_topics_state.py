import unittest

from weathercal.state import WeatherState
from weathercal.topics import infer_topics, page_dependencies


class TopicAndStateTests(unittest.TestCase):
    def test_topics_are_inferred_from_widgets(self):
        pages = [
            {
                "id": "now",
                "widgets": [
                    {"type": "current_summary"},
                    {"type": "value", "path": "wind", "formatter": "wind"},
                ],
            },
            {
                "id": "system",
                "widgets": [{"type": "server_status"}],
            },
        ]

        self.assertEqual(
            infer_topics("inkplate/weather-calendar", pages),
            {
                "current": "inkplate/weather-calendar/current",
                "server_status": "inkplate/weather-calendar/server/status",
                "wind": "inkplate/weather-calendar/current/wind",
            },
        )
        self.assertEqual(
            page_dependencies(pages[0]),
            {"current", "wind"},
        )

    def test_state_merges_topics_and_supports_dotted_paths(self):
        state = WeatherState()
        changed = state.update(
            "current",
            '{"temperature":{"value":12,"unit":"°C"},"icon":"icon/rain.png"}',
        )
        state.update("wind", '{"value":4.2,"unit":"m/s"}')
        state.update("weather_status", '{"generated_at":"2026-06-19T10:00:00Z"}')

        self.assertTrue(changed)
        self.assertEqual(state.get("current.temperature.value"), 12)
        self.assertEqual(state.get("wind.value"), 4.2)
        self.assertEqual(state.generated_at(), "2026-06-19T10:00:00Z")
        self.assertFalse(
            state.update(
                "wind",
                '{"value":4.2,"unit":"m/s"}',
            )
        )

    def test_missing_optional_fields_return_default(self):
        state = WeatherState()
        state.update("current", "{}")

        self.assertEqual(state.get("current.alerts.active", False), False)
        self.assertEqual(state.get("hourly.0.temperature.value", "--"), "--")
