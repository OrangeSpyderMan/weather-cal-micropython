import unittest
import json

from weathercal.app import WeatherCalApp


class FakeDisplay:
    def __init__(self):
        self.statuses = []
        self.indicators = []

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

    def indicator(self, state):
        self.indicators.append(state)

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
        self.kwargs = kwargs
        self.publications = []
        FakeMQTT.instances.append(self)

    def set_callback(self, callback):
        self.callback = callback

    def connect(self):
        pass

    def subscribe(self, topic):
        self.subscriptions.append(topic)

    def publish(self, topic, payload, retain=False):
        self.publications.append((topic, payload, retain))

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
            "diagnostics": {
                "enabled": True,
                "status_interval_s": 300,
            },
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
        self.assertEqual(app.display.indicators[-1], "stale")
        self.assertEqual(
            set(FakeMQTT.instances[0].subscriptions),
            {
                "inkplate/weather-calendar/current",
            },
        )
        client = FakeMQTT.instances[0]
        self.assertEqual(
            client.kwargs["will_topic"],
            "inkplate/weather-calendar/clients/test/status",
        )
        self.assertTrue(client.kwargs["will_retain"])
        status = [
            item
            for item in client.publications
            if item[0].endswith("/clients/test/status")
        ][-1]
        self.assertTrue(status[2])
        self.assertEqual(json.loads(status[1])["state"], "online")

    def test_publishes_non_retained_diagnostics_and_periodic_status(self):
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
        client = FakeMQTT.instances[0]
        diagnostics = [
            item
            for item in client.publications
            if item[0] == "inkplate/weather-calendar/diagnostics"
        ]
        self.assertTrue(diagnostics)
        self.assertFalse(diagnostics[-1][2])
        self.assertIn("test [INFO] connected to MQTT", diagnostics[-1][1])

        client.publications.clear()
        app.status_dirty = False
        clock[0] = 300000
        app.step()
        statuses = [
            item for item in client.publications if item[0].endswith("/status")
        ]
        self.assertEqual(len(statuses), 1)
        payload = json.loads(statuses[0][1])
        self.assertEqual(payload["uptime_s"], 300)
        self.assertEqual(payload["display"]["driver"], "hd44780")

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
        self.assertEqual(app.display.indicators[-1], "error")
        self.assertEqual(app.reconnect_delay_s, 4)
        clock[0] = 2000
        app.step()
        self.assertEqual(app.reconnect_delay_s, 8)
        clock[0] = 6000
        app.step()
        self.assertEqual(app.reconnect_delay_s, 8)

    def test_indicator_priority_is_error_stale_paused_online(self):
        app = WeatherCalApp(
            config(),
            {"WIFI_SSID": "wifi", "WIFI_PASSWORD": "secret"},
            display=FakeDisplay(),
            mqtt_factory=FakeMQTT,
            network_factory=FakeNetwork,
            now_ms=lambda: 0,
        )
        app.connected = True

        app._update_indicator(stale=False)
        self.assertEqual(app.display.indicators[-1], "online")
        app.scheduler.paused = True
        app._update_indicator(stale=False)
        self.assertEqual(app.display.indicators[-1], "paused")
        app._update_indicator(stale=True)
        self.assertEqual(app.display.indicators[-1], "stale")
        app.last_error = "failed"
        app._update_indicator(stale=False)
        self.assertEqual(app.display.indicators[-1], "error")
