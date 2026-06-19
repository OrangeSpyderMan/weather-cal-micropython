from .base import Display
from ..formatters import percent, temperature
from ..icons import LCD_GLYPHS, icon_text, semantic_icon


class CharacterDisplay(Display):
    def __init__(self, lcd, columns, rows):
        self.lcd = lcd
        self.columns = columns
        self.rows = rows
        self.buffer = []
        self.glyph_slots = {}

    def begin(self, page_id):
        self.buffer = [[" "] * self.columns for _ in range(self.rows)]
        self.glyph_slots = {}

    def text(self, widget, value):
        self._write(
            widget.get("row", 0),
            widget.get("col", 0),
            str(value),
            widget.get("width"),
            widget.get("align", "left"),
        )

    def icon(self, widget, name):
        slot = self._glyph_slot(name)
        value = chr(slot) if slot is not None else icon_text(name)
        self._write(widget.get("row", 0), widget.get("col", 0), value)

    def summary(self, widget, pieces):
        self._write(
            widget.get("row", 0),
            widget.get("col", 0),
            " ".join(pieces),
            widget.get("width"),
            widget.get("align", "left"),
        )

    def hourly(self, widget, entries):
        start = widget.get("row", 0)
        count = widget.get("rows", self.rows - start)
        column = widget.get("col", 0)
        width = min(
            widget.get("width", self.columns - column),
            self.columns - column,
        )
        for offset, item in enumerate(entries[:count]):
            stamp = item.get("dt", "")
            hour = stamp[11:16] if len(stamp) >= 16 else "--:--"
            temperature_value = item.get("temperature")
            rain_probability = percent(item.get("rain_probability"))
            temperature_text = temperature(temperature_value)
            text = "{} {} {}".format(hour, temperature_text, rain_probability)
            if len(text) > width:
                temperature_text = _compact_temperature(temperature_value)
                text = "{} {} {}".format(hour, temperature_text, rain_probability)
            self._write(start + offset, column, text, width)

    def badge(self, value, secondary=False):
        row = self.rows - 1
        col = max(0, self.columns - len(value))
        self._write(row, col, value)

    def end(self):
        self.lcd.clear()
        for name, slot in self.glyph_slots.items():
            self.lcd.create_char(slot, LCD_GLYPHS[name])
        for row, content in enumerate(self.lines()):
            self.lcd.move_to(0, row)
            self.lcd.write(content)

    def lines(self):
        return ["".join(row) for row in self.buffer]

    def _write(self, row, col, value, width=None, align="left"):
        if row < 0 or row >= self.rows or col >= self.columns:
            return
        width = min(width or self.columns - col, self.columns - col)
        value = str(value)
        if align == "right":
            value = _pad(value[-width:], width, "right")
        elif align == "center":
            value = _pad(value[:width], width, "center")
        else:
            value = _pad(value[:width], width, "left")
        for index, character in enumerate(value):
            self.buffer[row][col + index] = character

    def _glyph_slot(self, name):
        name = semantic_icon(name)
        if name not in LCD_GLYPHS:
            return None
        if name not in self.glyph_slots:
            if len(self.glyph_slots) >= 8:
                return None
            self.glyph_slots[name] = len(self.glyph_slots)
        return self.glyph_slots[name]


def _pad(value, width, align):
    padding = max(0, width - len(value))
    if align == "right":
        return (" " * padding) + value
    if align == "center":
        left = padding // 2
        return (" " * left) + value + (" " * (padding - left))
    return value + (" " * padding)


def _compact_temperature(value):
    if not isinstance(value, dict) or value.get("value") is None:
        return temperature(value)
    number = int(round(float(value["value"])))
    suffix = "F" if "F" in value.get("unit", "") else "C"
    return "{}{}".format(number, suffix)
