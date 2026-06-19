def measurement(value, digits=1):
    if value is None:
        return "--"
    number = round(float(value), digits)
    if number == int(number):
        return str(int(number))
    return str(number)


def temperature(value):
    if isinstance(value, dict):
        return "{}{}".format(
            measurement(value.get("value")),
            _temperature_suffix(value.get("unit", "")),
        )
    return measurement(value)


def percent(value):
    return "{}%".format(measurement(value, 0)) if value is not None else "--"


def wind(value):
    if not isinstance(value, dict) or value.get("value") is None:
        return "Wind --"
    speed = float(value["value"])
    unit = value.get("unit", "")
    if unit == "m/s":
        speed *= 3.6
        unit = "km/h"
    elif unit == "kmh":
        unit = "km/h"
    direction = value.get("direction_cardinal", "")
    return "{}{} {}".format(measurement(speed), unit, direction).strip()


def rain(value):
    if not isinstance(value, dict) or value.get("value") is None:
        return "Rain --"
    unit = value.get("rate_unit") or value.get("unit", "")
    if "/" not in unit and unit:
        unit += "/h"
    return "{}{}".format(measurement(value["value"]), unit)


def clock(value):
    if not isinstance(value, str) or len(value) < 16:
        return "--:--"
    return value[11:16]


def age_label(seconds):
    if seconds is None:
        return "unknown"
    if seconds < 60:
        return "{}s".format(int(seconds))
    if seconds < 3600:
        return "{}m".format(int(seconds // 60))
    return "{}h".format(int(seconds // 3600))


FORMATTERS = {
    "measurement": measurement,
    "temperature": temperature,
    "percent": percent,
    "wind": wind,
    "rain": rain,
    "clock": clock,
    "text": lambda value: str(value),
}


def format_value(value, formatter="text"):
    function = FORMATTERS.get(formatter)
    if function is None:
        raise ValueError("unknown formatter: {}".format(formatter))
    return function(value)


def _temperature_suffix(unit):
    return "F" if "F" in unit else "C"
