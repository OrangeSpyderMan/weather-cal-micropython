import unittest

from weathercal.app import WeatherCalApp


class FakeDisplay:
    def __init__(self):
        self.statuses = []

    def status(self, title, detail=""):
        self.statuses.append((title, detail))

    def begin(self, page):
        pass

    def text(self, widget, value):
        pass

    def icon(self, widget, name):
        pass

    def summary(self, widget, pieces):
        pass

    def hourly(self, widget, entries):
        pass

    def badge(self, value, secondary=False):
        pass

    def end(self):
        pass


class FakeNetwork:
    def __init__(self, ssid, password):
        self.is_connected = False

    def connected(self):
        return self.is_connected

    def connect(self):
        self.is_connected = True

    def sync_clock(self):
        return True


class FakeMQTT:
    instances = []

    def __init__(self, *args, **kwargs):
        self.callback = None
        self.subscriptions = []
        self.disconnected = False
        FakeMQTT.instances.append(self)

    def set_callback(self, callback):
        self.callback = callback

    def connect(self):
        pass

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def check_msg(self):
        pass

    def disconnect(self):
        self.disconnected = True


def config():
    return {
        "DEVICE": {
            "driver": "hd44780",
            "page_profile": "lcd",
            "columns": 16,
            "rows": 2,
        },
        "MQTT": {
            "host": "mqtt.local",
            "base_topic": "inkplate/weather-calendar",
            "client_id": "test",
            "reconnect_min_s": 2,
            "reconnect_max_s": 8,
        },
        "RUNTIME": {
            "default_page_duration_s": 5,
            "redraw_coalesce_ms": 1,
            "forced_refresh_s": 300,
            "stale_after_s": 3600,
        },
        "BUTTONS": {},
        "PAGE_PROFILES": {
            "lcd": [
                {
                    "id": "now",
                    "widgets": [
                        {
                            "type": "current_summary",
                            "row": 0,
                            "col": 0,
                        }
                    ],
                }
            ]
        },
    }


class AppTests(unittest.TestCase):
    def setUp(self):
        FakeMQTT.instances = []

    def test_connects_and_subscribes_to_derived_topics(self):
        clock = [0]
        app = WeatherCalApp(
            config(),
            {"WIFI_SSID": "wifi", "WIFI_PASSWORD": "secret"},
            display=FakeDisplay(),
            mqtt_factory=FakeMQTT,
            network_factory=FakeNetwork,
            now_ms=lambda: clock[0],
        )

        app.step()

        self.assertTrue(app.connected)
        self.assertEqual(
            set(FakeMQTT.instances[0].subscriptions),
            {
                "inkplate/weather-calendar/current",
            },
        )

    def test_retained_message_updates_state_and_marks_page_dirty(self):
        clock = [0]
        app = WeatherCalApp(
            config(),
            {"WIFI_SSID": "wifi", "WIFI_PASSWORD": "secret"},
            display=FakeDisplay(),
            mqtt_factory=FakeMQTT,
            network_factory=FakeNetwork,
            now_ms=lambda: clock[0],
        )
        app.step()
        app.dirty_pages.clear()
        client = FakeMQTT.instances[0]

        client.callback(
            b"inkplate/weather-calendar/current",
            b'{"temperature":{"value":9,"unit":"C"}}',
        )

        self.assertEqual(app.state.get("current.temperature.value"), 9)
        self.assertEqual(app.dirty_pages, {"now"})

    def test_reconnect_backoff_is_bounded(self):
        class BrokenMQTT(FakeMQTT):
            def connect(self):
                raise OSError("offline")

        clock = [0]
        app = WeatherCalApp(
            config(),
            {"WIFI_SSID": "wifi", "WIFI_PASSWORD": "secret"},
            display=FakeDisplay(),
            mqtt_factory=BrokenMQTT,
            network_factory=FakeNetwork,
            now_ms=lambda: clock[0],
        )

        app.step()
        self.assertFalse(app.connected)
        self.assertEqual(app.reconnect_delay_s, 4)
        clock[0] = 2000
        app.step()
        self.assertEqual(app.reconnect_delay_s, 8)
        clock[0] = 6000
        app.step()
        self.assertEqual(app.reconnect_delay_s, 8)
