import unittest

from weathercal.timeutil import age_seconds, iso_epoch


class TimeUtilTests(unittest.TestCase):
    def test_parses_utc_and_offset_timestamps(self):
        utc = iso_epoch("2026-06-19T12:00:00Z")
        offset = iso_epoch("2026-06-19T14:00:00+02:00")

        self.assertEqual(utc, offset)
        self.assertEqual(age_seconds("2026-06-19T12:00:00Z", utc + 30), 30)

    def test_invalid_timestamp_has_unknown_age(self):
        self.assertIsNone(iso_epoch("not-a-time"))
        self.assertIsNone(age_seconds(None))
