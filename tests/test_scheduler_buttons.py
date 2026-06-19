import unittest

from weathercal.buttons import ButtonController
from weathercal.scheduler import PageScheduler


class FakePin:
    def __init__(self, value=1):
        self.current = value

    def value(self):
        return self.current


class SchedulerAndButtonTests(unittest.TestCase):
    def test_page_rotation_and_navigation(self):
        pages = [
            {"id": "one", "duration_s": 1},
            {"id": "two", "duration_s": 2},
        ]
        scheduler = PageScheduler(pages, 5, 100)

        self.assertFalse(scheduler.update(1099))
        self.assertTrue(scheduler.update(1100))
        self.assertEqual(scheduler.page["id"], "two")
        scheduler.previous(1200)
        self.assertEqual(scheduler.page["id"], "one")
        scheduler.next(1300)
        scheduler.home(1400)
        self.assertEqual(scheduler.page["id"], "one")
        scheduler.toggle_pause(1500)
        self.assertTrue(scheduler.paused)

    def test_ticks_wraparound(self):
        pages = [{"id": "one", "duration_s": 1}, {"id": "two"}]
        start = (1 << 30) - 500
        scheduler = PageScheduler(pages, 5, start)

        self.assertFalse(scheduler.update(400))
        self.assertTrue(scheduler.update(500))

    def test_button_debounce_emits_once_per_press(self):
        pin = FakePin()
        controller = ButtonController(
            {"next": {"pin": 1, "active_low": True}},
            lambda number, active_low: pin,
            debounce_ms=100,
        )

        pin.current = 0
        self.assertEqual(controller.poll(10), [])
        self.assertEqual(controller.poll(109), [])
        self.assertEqual(controller.poll(110), ["next"])
        self.assertEqual(controller.poll(200), [])
        pin.current = 1
        controller.poll(220)
        pin.current = 0
        controller.poll(300)
        self.assertEqual(controller.poll(400), ["next"])
