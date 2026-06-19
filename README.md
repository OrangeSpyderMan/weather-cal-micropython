# Weather Cal MicroPython

A configurable MicroPython MQTT client for small Weather Calendar displays.

The project consumes the retained MQTT API published by
`OrangeSpyderMan/inkplate10-weather-cal` and presents it through display-specific
page profiles. It targets Raspberry Pi Pico W first and keeps hardware,
rendering, state, and transport code separated so more MicroPython boards and
displays can be added later.

## Initial hardware

- 52Pi EP-0164 breadboard kit, 320×240 ILI9341 TFT
- Freenove/HD44780 1602 character LCD with PCF8574 I²C backpack
- Freenove/HD44780 2004 character LCD with PCF8574 I²C backpack
- USB serial terminal or plain serial log output

The project includes original ILI9341, HD44780, MQTT 3.1.1, bitmap-icon, and
5×7 font implementations under the MIT license. No Freenove or 52Pi source code
is copied into this repository.

## Features

- Declarative display-specific page profiles in `config.py`
- EP-0164 portrait, landscape, and 180-degree flipped orientations
- Per-page rotation durations
- Optional previous, next, home, and pause buttons
- Config-derived retained MQTT subscriptions
- Current weather, hourly forecast, wind, rain, metadata, and server status
- Local weather icons on TFT and custom glyph/text fallbacks on character LCDs
- Wi-Fi/MQTT recovery with bounded exponential backoff
- NTP clock synchronization and stale-data badges
- Redraw coalescing and periodic forced refresh
- First-class serial terminal display plus serial fallback for troubleshooting

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
For the EP-0164 it also selects a matching portrait or landscape page layout
and supports 180-degree flipped variants.

For scripted setup:

```bash
python3 tools/generate_config.py \
  --non-interactive \
  --profile ep0164 \
  --orientation landscape-flipped \
  --mqtt-host 192.168.1.10 \
  --wifi-ssid your-wifi \
  --wifi-password your-password \
  --deploy \
  --reset \
  --device /dev/ttyACM0
```

Available profiles are:

```text
examples/config_ep0164.py
examples/config_freenove_1602.py
examples/config_freenove_2004.py
examples/config_serial.py
```

4. Review the generated display pins and page definitions.
5. Deploy with `mpremote`:

```bash
python3 tools/deploy.py \
  --config config.py \
  --secrets secrets.py \
  --device /dev/ttyACM0
```

After copying, the deploy helper asks whether to reset the Pico W immediately.
For scripted use, pass `--reset` or `--no-reset`.

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

The Freenove profiles use a PCF8574-compatible I²C backpack. Their defaults are:

```text
I2C 0
SDA GP0
SCL GP1
100 kHz
address auto-detect (0x27 or 0x3f)
```

The generator prompts for the bus and pins. It can scan the two common
addresses automatically, or accept an explicit address:

```bash
python3 tools/generate_config.py \
  --profile freenove-2004 \
  --i2c-id 1 \
  --i2c-sda 6 \
  --i2c-scl 7 \
  --i2c-address 0x3f
```

The lower-level HD44780 driver still supports direct 4-bit GPIO by setting
`DEVICE["transport"] = "gpio"` and supplying `rs`, `enable`, and `d4`–`d7`
pins.

## Serial display

Choose the `serial` generator profile to use the Pico W USB serial connection
as the display:

```bash
python3 tools/generate_config.py --profile serial
```

By default it clears and redraws an ANSI terminal on page changes. Use
`--serial-plain` for append-only human-readable output suitable for logs:

```bash
python3 tools/generate_config.py \
  --profile serial \
  --serial-plain
```

The serial renderer follows the same configured pages, rotation timings, stale
indicators, and MQTT-derived subscriptions as physical displays.

## EP-0164 controls

The EP-0164 profile maps four optional active-low buttons:

```text
previous, next, home, pause
```

Change or remove these mappings if your board wiring differs.

The generator offers these EP-0164 orientations:

```text
portrait
landscape
portrait-flipped
landscape-flipped
```

The flipped variants rotate the selected portrait or landscape layout by 180
degrees. In a handwritten config, `DEVICE.rotation` accepts `0`, `1`, `2`, or
`3` respectively.

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
