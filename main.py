from config import BUTTONS, DEVICE, MQTT, PAGE_PROFILES, RUNTIME
from secrets import MQTT_PASSWORD, MQTT_USER, WIFI_PASSWORD, WIFI_SSID

from weathercal.app import WeatherCalApp, machine_pin_factory


CONFIG = {
    "DEVICE": DEVICE,
    "MQTT": MQTT,
    "RUNTIME": RUNTIME,
    "BUTTONS": BUTTONS,
    "PAGE_PROFILES": PAGE_PROFILES,
}
SECRETS = {
    "WIFI_SSID": WIFI_SSID,
    "WIFI_PASSWORD": WIFI_PASSWORD,
    "MQTT_USER": MQTT_USER,
    "MQTT_PASSWORD": MQTT_PASSWORD,
}


WeatherCalApp(
    CONFIG,
    SECRETS,
    pin_factory=machine_pin_factory,
).run()
