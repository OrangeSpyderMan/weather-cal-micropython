import time

from .buttons import ButtonController
from .compat import sleep_ms, ticks_add, ticks_diff, ticks_ms
from .configuration import validate_config
from .displays import create_display
from .mqtt_client import MQTTClient
from .networking import NetworkManager
from .pages import PageRenderer, pages_affected
from .scheduler import PageScheduler
from .state import WeatherState
from .timeutil import age_seconds
from .topics import infer_topics


class WeatherCalApp:
    def __init__(
        self,
        config,
        secrets,
        display=None,
        mqtt_factory=MQTTClient,
        network_factory=NetworkManager,
        pin_factory=None,
        now_ms=ticks_ms,
    ):
        validate_config(config)
        self.config = config
        self.secrets = secrets
        self.now_ms = now_ms
        self.display = display or create_display(config["DEVICE"])
        self.renderer = PageRenderer(self.display)
        profile = config["DEVICE"]["page_profile"]
        self.pages = config["PAGE_PROFILES"][profile]
        runtime = config["RUNTIME"]
        self.scheduler = PageScheduler(
            self.pages,
            runtime["default_page_duration_s"],
            now_ms(),
        )
        self.state = WeatherState()
        self.topics = infer_topics(config["MQTT"]["base_topic"], self.pages)
        self.reverse_topics = {
            value.encode(): key for key, value in self.topics.items()
        }
        self.mqtt_factory = mqtt_factory
        self.network_factory = network_factory
        self.network = None
        self.client = None
        self.connected = False
        self.dirty_pages = {page["id"] for page in self.pages}
        self.last_draw = 0
        self.last_forced_draw = 0
        self.reconnect_delay_s = config["MQTT"].get("reconnect_min_s", 2)
        self.next_reconnect = now_ms()
        self.buttons = None
        if config["BUTTONS"] and pin_factory:
            self.buttons = ButtonController(
                config["BUTTONS"],
                pin_factory,
                runtime.get("button_debounce_ms", 180),
            )

    def run(self):
        self.display.status("Weather Cal", "Starting")
        while True:
            self.step()
            sleep_ms(self.config["RUNTIME"].get("loop_sleep_ms", 50))

    def step(self):
        now = self.now_ms()
        if not self.connected and ticks_diff(now, self.next_reconnect) >= 0:
            self._connect()
        if self.connected:
            try:
                self.client.check_msg()
            except Exception as exc:
                self._offline(exc)
        if self.scheduler.update(now):
            self.dirty_pages.add(self.scheduler.page["id"])
        self._handle_buttons(now)
        self._draw_if_due(now)

    def _connect(self):
        try:
            if self.network is None:
                self.network = self.network_factory(
                    self.secrets["WIFI_SSID"],
                    self.secrets["WIFI_PASSWORD"],
                )
            if not self.network.connected():
                self.display.status("Wi-Fi", "Connecting")
                self.network.connect()
                self.network.sync_clock()
            settings = self.config["MQTT"]
            self.client = self.mqtt_factory(
                settings["client_id"],
                settings["host"],
                port=settings.get("port", 1883),
                user=self.secrets.get("MQTT_USER"),
                password=self.secrets.get("MQTT_PASSWORD"),
                keepalive=settings.get("keepalive_s", 60),
            )
            self.client.set_callback(self._message)
            self.client.connect()
            for topic in self.topics.values():
                self.client.subscribe(topic)
            self.connected = True
            self.reconnect_delay_s = settings.get("reconnect_min_s", 2)
            self.dirty_pages.add(self.scheduler.page["id"])
        except Exception as exc:
            self._offline(exc)

    def _offline(self, exc):
        print("Connection lost:", exc)
        self.connected = False
        if self.client:
            self.client.disconnect()
        settings = self.config["MQTT"]
        self.next_reconnect = ticks_add(
            self.now_ms(), int(self.reconnect_delay_s * 1000)
        )
        self.reconnect_delay_s = min(
            self.reconnect_delay_s * 2,
            settings.get("reconnect_max_s", 60),
        )
        self.dirty_pages.add(self.scheduler.page["id"])

    def _message(self, topic, payload):
        name = self.reverse_topics.get(topic)
        if name and self.state.update(name, payload):
            self.dirty_pages.update(pages_affected(self.pages, name))

    def _handle_buttons(self, now):
        if not self.buttons:
            return
        for action in self.buttons.poll(now):
            if action == "next":
                self.scheduler.next(now)
            elif action == "previous":
                self.scheduler.previous(now)
            elif action == "home":
                self.scheduler.home(now)
            elif action == "pause":
                self.scheduler.toggle_pause(now)
            self.dirty_pages.add(self.scheduler.page["id"])

    def _draw_if_due(self, now):
        runtime = self.config["RUNTIME"]
        page_id = self.scheduler.page["id"]
        forced = ticks_diff(
            now,
            ticks_add(
                self.last_forced_draw,
                int(runtime["forced_refresh_s"] * 1000),
            ),
        ) >= 0
        coalesced = ticks_diff(
            now,
            ticks_add(
                self.last_draw,
                int(runtime["redraw_coalesce_ms"]),
            ),
        ) >= 0
        if (page_id in self.dirty_pages and coalesced) or forced:
            age = age_seconds(self.state.generated_at())
            stale = age is None or age > runtime["stale_after_s"]
            self.renderer.render(
                self.scheduler.page,
                self.state,
                stale=stale,
                paused=self.scheduler.paused,
            )
            self.dirty_pages.discard(page_id)
            self.last_draw = now
            if forced:
                self.last_forced_draw = now


def machine_pin_factory(pin_number, active_low=True):
    from machine import Pin

    return Pin(pin_number, Pin.IN, Pin.PULL_UP if active_low else Pin.PULL_DOWN)
