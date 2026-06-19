import unittest

from weathercal.displays.hd44780 import Pcf8574Bus


class FakeI2C:
    def __init__(self, addresses):
        self.addresses = addresses
        self.writes = []

    def scan(self):
        return self.addresses

    def writeto(self, address, value):
        self.writes.append((address, bytes(value)))


class Pcf8574Tests(unittest.TestCase):
    def test_auto_detects_common_address_and_writes_nibbles(self):
        i2c = FakeI2C([0x27])

        bus = Pcf8574Bus({"address": None}, i2c=i2c)
        bus.send(0x41, data=True)

        self.assertEqual(bus.address, 0x27)
        self.assertTrue(i2c.writes)
        self.assertTrue(all(address == 0x27 for address, _ in i2c.writes))
        self.assertEqual(i2c.writes[-3:], [
            (0x27, b"\x19"),
            (0x27, b"\x1d"),
            (0x27, b"\x19"),
        ])

    def test_explicit_address_can_select_nonstandard_backpack(self):
        bus = Pcf8574Bus(
            {"address": 0x26},
            i2c=FakeI2C([0x26, 0x27]),
        )

        self.assertEqual(bus.address, 0x26)

    def test_auto_detection_rejects_ambiguous_common_addresses(self):
        with self.assertRaisesRegex(OSError, "multiple"):
            Pcf8574Bus(
                {"address": None},
                i2c=FakeI2C([0x27, 0x3F]),
            )

    def test_missing_address_reports_scan_results(self):
        with self.assertRaisesRegex(OSError, "0x20"):
            Pcf8574Bus(
                {"address": None},
                i2c=FakeI2C([0x20]),
            )
