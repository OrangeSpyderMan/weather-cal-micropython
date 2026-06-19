# Weather Cal MicroPython

A configurable MicroPython MQTT client for small Weather Calendar displays.

The project consumes the retained MQTT API published by
`OrangeSpyderMan/inkplate10-weather-cal` and presents it through display-specific
page profiles. It targets Raspberry Pi Pico W first and keeps hardware,
rendering, state, and transport code separated so more MicroPython boards and
displays can be added later.

## Initial hardware

- 52Pi EP-0164 breadboard kit, 320×240 ILI9341 TFT
- Freenove/HD44780 1602 character LCD using direct 4-bit GPIO
- Freenove/HD44780 2004 character LCD using direct 4-bit GPIO

The project includes original ILI9341, HD44780, MQTT 3.1.1, bitmap-icon, and
5×7 font implementations under the MIT license. No Freenove or 52Pi source code
is copied into this repository.

## Features

- Declarative display-specific page profiles in `config.py`
- Per-page rotation durations
- Optional previous, next, home, and pause buttons
- Config-derived retained MQTT subscriptions
- Current weather, hourly forecast, wind, rain, metadata, and server status
- Local weather icons on TFT and custom glyph/text fallbacks on character LCDs
- Wi-Fi/MQTT recovery with bounded exponential backoff
- NTP clock synchronization and stale-data badges
- Redraw coalescing and periodic forced refresh
- Serial display fallback for hardware troubleshooting

## MQTT compatibility

The client supports Weather Calendar schema 2.0 topics below the configured
base topic:

```text
current
hourly
status
generated_at
current/rain
current/wind
server/status
```

Only topics required by the selected page profile are subscribed.

## Install

1. Flash current Pico W MicroPython firmware.
2. Clone this repository.
3. Run the configuration generator:

```bash
python3 tools/generate_config.py
```

It prompts for the display profile, broker, page timing, Wi-Fi credentials, and
optional MQTT credentials. It writes `config.py` and a mode-0600 `secrets.py`,
refusing to overwrite either unless `--force` is supplied. At the end it can
deploy the generated configuration and application directly with `mpremote`.

For scripted setup:

```bash
python3 tools/generate_config.py \
  --non-interactive \
  --profile ep0164 \
  --mqtt-host 192.168.1.10 \
  --wifi-ssid your-wifi \
  --wifi-password your-password \
  --deploy \
  --device /dev/ttyACM0
```

Available profiles are:

```text
examples/config_ep0164.py
examples/config_freenove_1602.py
examples/config_freenove_2004.py
```

4. Review the generated display pins and page definitions.
5. Deploy with `mpremote`:

```bash
python3 tools/deploy.py \
  --config config.py \
  --secrets secrets.py \
  --device /dev/ttyACM0
```

Reset the Pico W after deployment.

## Configuration model

`config.py` exports five dictionaries:

- `DEVICE`: driver, dimensions, pins, orientation, and selected page profile
- `MQTT`: broker, base topic, client ID, keepalive, and reconnect limits
- `RUNTIME`: page duration, redraw timing, stale threshold, and loop timing
- `BUTTONS`: optional action-to-pin mappings
- `PAGE_PROFILES`: display-specific page and widget definitions

Every page has a stable `id`, optional `duration_s`, and ordered `widgets`.
ILI9341 widgets use pixel `x`/`y` geometry. Character LCD widgets use
`row`/`col` and optional `width`/`align`.

Supported widget types:

- `text`
- `value`
- `icon`
- `current_summary`
- `hourly_table`
- `metadata`
- `server_status`

Value widgets use dotted paths such as `current.temperature`,
`server.runtime.version`, `wind`, or `rain`, plus a formatter and fallback.

## Character LCD wiring

The HD44780 driver uses direct 4-bit mode:

```text
RS, Enable, D4, D5, D6, D7
```

Pin numbers are entirely configurable. The example uses GP10–GP15 as a clear
starting point; adjust them to your Freenove wiring. An optional GPIO-controlled
backlight pin may be configured.

## EP-0164 controls

The EP-0164 profile maps four optional active-low buttons:

```text
previous, next, home, pause
```

Change or remove these mappings if your board wiring differs.

## Development

Host tests require only CPython:

```bash
make test
make check
```

The tests cover configuration, subscriptions, MQTT state merging, formatting,
timer wraparound, buttons, character-buffer golden output, TFT drawing
commands, reconnect behavior, and stale data.

## Hardware acceptance checklist

- Retained data appears within 10 seconds of broker connection.
- Pages rotate at configured durations.
- Buttons navigate and pause without repeated presses.
- Wi-Fi and broker interruptions recover without reboot.
- Character LCD output remains within physical dimensions.
- The TFT renders current conditions, icons, and forecast pages.
- Long-running operation does not show sustained memory loss.

## License

MIT. See [LICENSE](LICENSE).
