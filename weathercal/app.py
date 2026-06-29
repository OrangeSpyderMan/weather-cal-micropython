from .buttons import ButtonController
from .compat import sleep_ms, ticks_add, ticks_diff, ticks_ms
from .configuration import validate_config
from .diagnostics import (
    diagnostic_message,
    diagnostic_topic,
    offline_payload,
    status_payload,
    status_topic,
)
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
        self.started_ms = now_ms()
        self.display = display or create_display(config["DEVICE"])
        self.renderer = PageRenderer(self.display)
        profile = config["DEVICE"]["page_profile"]
        self.pages = config["PAGE_PROFILES"][profile]
        runtime = config["RUNTIME"]
        self.scheduler = PageScheduler(
            self.pages,
            runtime["default_page_duration_s"],
            self.started_ms,
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
        self.last_status = self.started_ms
        self.status_dirty = True
        self.last_error = None
        self.pending_diagnostics = []
        self.buttons = None
        self._set_indicator("connecting")
        if config["BUTTONS"] and pin_factory:
            self.buttons = ButtonController(
                config["BUTTONS"],
                pin_factory,
                runtime.get("button_debounce_ms", 180),
            )

    def run(self):
        self.display.status("Weather Cal", "Starting")
        self._log(
            "INFO",
            "starting {}/{}".format(
                self.config["DEVICE"]["driver"],
                self.config["DEVICE"]["page_profile"],
            ),
        )
        while True:
            self.step(wait=True)
            if self._message_mode() == "poll":
                sleep_ms(self.config["RUNTIME"].get("loop_sleep_ms", 50))

    def step(self, wait=False):
        now = self.now_ms()
        if not self.connected and ticks_diff(now, self.next_reconnect) >= 0:
            self._connect()
        if self.connected:
            try:
                self._receive_message(now, wait)
            except Exception as exc:
                self._offline(exc)
        if self.scheduler.update(now):
            self.dirty_pages.add(self.scheduler.page["id"])
            self.status_dirty = True
        self._handle_buttons(now)
        self._draw_if_due(now)
        self._publish_status_if_due(now)

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
            diagnostics = settings.get("diagnostics", {})
            diagnostics_enabled = diagnostics.get("enabled", True)
            self.client = self.mqtt_factory(
                settings["client_id"],
                settings["host"],
                port=settings.get("port", 1883),
                user=self.secrets.get("MQTT_USER"),
                password=self.secrets.get("MQTT_PASSWORD"),
                keepalive=settings.get("keepalive_s", 60),
                will_topic=status_topic(settings) if diagnostics_enabled else None,
                will_payload=offline_payload(self.config)
                if diagnostics_enabled
                else None,
                will_retain=diagnostics_enabled,
            )
            self.client.set_callback(self._message)
            self.client.connect()
            for topic in self.topics.values():
                self.client.subscribe(topic)
            self.connected = True
            self.last_error = None
            self.reconnect_delay_s = settings.get("reconnect_min_s", 2)
            self.dirty_pages.add(self.scheduler.page["id"])
            self.status_dirty = True
            self._flush_diagnostics()
            self._log("INFO", "connected to MQTT")
            self._update_indicator()
            self._publish_status(self.now_ms())
        except Exception as exc:
            self._offline(exc)

    def _offline(self, exc):
        self.last_error = str(exc)
        self.connected = False
        self._set_indicator("error")
        if self.client:
            self.client.disconnect()
        self._log("ERROR", "connection lost: {}".format(exc))
        settings = self.config["MQTT"]
        self.next_reconnect = ticks_add(
            self.now_ms(), int(self.reconnect_delay_s * 1000)
        )
        self.reconnect_delay_s = min(
            self.reconnect_delay_s * 2,
            settings.get("reconnect_max_s", 60),
        )
        self.dirty_pages.add(self.scheduler.page["id"])
        self.status_dirty = True

    def _message(self, topic, payload):
        name = self.reverse_topics.get(topic)
        if name and self.state.update(name, payload):
            self.dirty_pages.update(pages_affected(self.pages, name))
            self.status_dirty = True

    def _receive_message(self, now, wait):
        if self._message_mode() == "event":
            self.client.wait_msg(self._event_wait_ms(now) if wait else 0)
        else:
            self.client.check_msg()

    def _message_mode(self):
        return self.config["RUNTIME"].get("message_mode", "poll")

    def _event_wait_ms(self, now):
        runtime = self.config["RUNTIME"]
        timeout = int(runtime.get("event_wait_ms", 1000))
        if self.buttons:
            timeout = min(timeout, int(runtime.get("loop_sleep_ms", 50)))
        deadlines = [self.scheduler.deadline]
        deadlines.append(
            ticks_add(
                self.last_forced_draw,
                int(runtime["forced_refresh_s"] * 1000),
            )
        )
        if self.dirty_pages:
            deadlines.append(
                ticks_add(
                    self.last_draw,
                    int(runtime["redraw_coalesce_ms"]),
                )
            )
        if self._diagnostics_enabled():
            settings = self.config["MQTT"].get("diagnostics", {})
            deadlines.append(
                ticks_add(
                    self.last_status,
                    int(settings.get("status_interval_s", 300) * 1000),
                )
            )
        for deadline in deadlines:
            remaining = ticks_diff(deadline, now)
            if remaining <= 0:
                return 0
            timeout = min(timeout, remaining)
        return max(0, timeout)

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
            self.status_dirty = True
            self._update_indicator()

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
            self._update_indicator(stale)
            try:
                self.renderer.render(
                    self.scheduler.page,
                    self.state,
                    stale=stale,
                    paused=self.scheduler.paused,
                )
            except Exception as exc:
                self.last_error = "display: {}".format(exc)
                self._set_indicator("error")
                self._log("ERROR", self.last_error)
                self.dirty_pages.discard(page_id)
                self.status_dirty = True
                return
            self.dirty_pages.discard(page_id)
            self.last_draw = now
            self.status_dirty = True
            if forced:
                self.last_forced_draw = now

    def _update_indicator(self, stale=None):
        if self.last_error:
            state = "error"
        elif not self.connected:
            state = "connecting"
        else:
            if stale is None:
                age = age_seconds(self.state.generated_at())
                stale = (
                    age is None
                    or age > self.config["RUNTIME"]["stale_after_s"]
                )
            if stale:
                state = "stale"
            elif self.scheduler.paused:
                state = "paused"
            else:
                state = "online"
        self._set_indicator(state)

    def _set_indicator(self, state):
        try:
            self.display.indicator(state)
        except Exception:
            pass

    def _diagnostics_enabled(self):
        return self.config["MQTT"].get("diagnostics", {}).get("enabled", True)

    def _log(self, level, message):
        text = diagnostic_message(
            self.config["MQTT"]["client_id"],
            level,
            message,
        )
        print(text)
        if not self._diagnostics_enabled():
            return
        if self.connected and self.client:
            try:
                self.client.publish(
                    diagnostic_topic(self.config["MQTT"]),
                    text,
                    retain=False,
                )
                return
            except Exception:
                pass
        self.pending_diagnostics.append(text)
        del self.pending_diagnostics[:-10]

    def _flush_diagnostics(self):
        if not self._diagnostics_enabled() or not self.connected:
            return
        topic = diagnostic_topic(self.config["MQTT"])
        pending = self.pending_diagnostics
        self.pending_diagnostics = []
        for index, message in enumerate(pending):
            try:
                self.client.publish(topic, message, retain=False)
            except Exception:
                self.pending_diagnostics.extend(pending[index:])
                del self.pending_diagnostics[:-10]
                return

    def _publish_status_if_due(self, now):
        if not self._diagnostics_enabled() or not self.connected:
            return
        settings = self.config["MQTT"].get("diagnostics", {})
        interval_ms = int(settings.get("status_interval_s", 300) * 1000)
        due = ticks_diff(now, ticks_add(self.last_status, interval_ms)) >= 0
        if self.status_dirty or due:
            try:
                self._publish_status(now)
            except Exception as exc:
                self._offline(exc)

    def _publish_status(self, now):
        self.client.publish(
            status_topic(self.config["MQTT"]),
            status_payload(self, now),
            retain=True,
        )
        self.last_status = now
        self.status_dirty = False


def machine_pin_factory(pin_number, active_low=True):
    from machine import Pin

    return Pin(pin_number, Pin.IN, Pin.PULL_UP if active_low else Pin.PULL_DOWN)
