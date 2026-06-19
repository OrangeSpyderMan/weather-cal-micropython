try:
    import ujson as json
except ImportError:
    import json

try:
    from time import ticks_add, ticks_diff, ticks_ms
except ImportError:
    import time

    _TICKS_PERIOD = 1 << 30

    def ticks_ms():
        return int(time.monotonic() * 1000) % _TICKS_PERIOD

    def ticks_add(value, delta):
        return (value + delta) % _TICKS_PERIOD

    def ticks_diff(new, old):
        half = _TICKS_PERIOD // 2
        return ((new - old + half) % _TICKS_PERIOD) - half


def sleep_ms(value):
    try:
        import time

        time.sleep_ms(value)
    except AttributeError:
        time.sleep(value / 1000)
