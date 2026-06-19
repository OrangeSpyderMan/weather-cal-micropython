# Contributing

Keep MicroPython compatibility in mind: avoid dataclasses, pathlib, asyncio,
and dependencies in code copied to the device.

Before submitting changes:

```bash
make test
make check
```

New display drivers should implement the display interface and include host-side
recording or golden-buffer tests. New widgets must declare their MQTT topic
dependencies so subscription inference remains correct.

Display profiles used by the generator live in `examples/`; add new profile
names to `tools/generate_config.py` and cover them in generator tests.
